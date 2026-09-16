#!/usr/bin/env python3
"""Exercise IDA protocol 9 without IDA: handshake, native TIDs, events and exit.

Usage: python3 tests/smoke.py --pin /kit/pin --tool obj-intel64/idadbg64.so
Pass --app /path/to/application to exercise another short-lived application.
"""
import argparse
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time

PACKET = struct.Struct('<IIQ')
# Independent IDA 8.5 constants (confirmed against ida_idd), keyed by the
# sequential names used internally by this test. Do not derive these from C++.
LEGACY_EVENTS = (0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192)
EVENT_SIZE = 1065  # packed protocol 9: 21-byte header + 1044-byte module union


def receive(sock, size):
    data = b''
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise AssertionError('Tool closed the connection before the reply')
        data += part
    return data


def run(args, version):
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='idapin-smoke-') as tmp:
        with open(Path(tmp) / 'tool.log', 'w+') as log:
            proc = subprocess.Popen([str(Path(args.pin).resolve()), '-t',
                                     str(Path(args.tool).resolve()), '-p', str(port),
                                     '-T', '5', '-idadbg', '1',
                                     *(['-event_ids', args.event_ids] if args.event_ids else []),
                                     '--', str(Path(args.app).resolve())],
                                    cwd=tmp, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        sock = socket.create_connection(('127.0.0.1', port), timeout=1)
                        break
                    except OSError:
                        if proc.poll() is not None or time.monotonic() > deadline:
                            raise AssertionError('Tool did not open its listening socket')
                        time.sleep(0.05)
                with sock:
                    sock.settimeout(15)
                    sock.sendall(PACKET.pack(2, version, 0))
                    # Legacy clients receive a pointer-size-dependent v1 reply.
                    reply_size = 16 if version == 9 or args.bits == 64 else 12
                    reply = receive(sock, reply_size)
                    code, protocol = struct.unpack_from('<II', reply)
                    assert (code, protocol) == (0, 9), (code, protocol)
                    width = int.from_bytes(reply[8:], 'little') & 0xff
                    assert width == args.bits // 8, width
                    if version == 9:
                        sock.sendall(PACKET.pack(4, 0, 0))  # START_PROCESS
                        seen = []
                        pending_resumes = 0
                        while True:
                            code, size, data = PACKET.unpack(receive(sock, PACKET.size))
                            if code == 0:  # ACK, possibly following a queued event
                                pending_resumes -= 1
                                continue
                            assert code == 5, ('unexpected packet', code, size, data)
                            event = receive(sock, EVENT_SIZE)
                            wire_eid, pid, tid = struct.unpack_from('<III', event)
                            assert wire_eid == size, (wire_eid, size)
                            if args.event_ids == 'modern':
                                eid = wire_eid
                            else:
                                assert wire_eid in LEGACY_EVENTS, ('invalid IDA 8.5 event', wire_eid)
                                eid = LEGACY_EVENTS.index(wire_eid)
                            assert eid != 7, ('application exception', event[21:40])
                            seen.append(eid)
                            if eid == 1:
                                assert pid == tid, ('main thread is not a native OS TID', pid, tid)
                                # General registers include r8-r15 on Intel 64.
                                sock.sendall(PACKET.pack(20, 1, tid))
                                reg_code, reg_size, reg_mask = PACKET.unpack(receive(sock, 16))
                                assert reg_code == 0 and reg_mask & 1 and reg_size > 0
                                receive(sock, reg_size)
                                entry = struct.unpack_from('<Q', event, 12)[0]
                                sock.sendall(PACKET.pack(8, 16, entry))
                                memory = receive(sock, 1032)
                                assert struct.unpack_from('<II', memory) == (8, 16)
                                sock.sendall(PACKET.pack(11, 0, 0))
                                # The fixed trace packet has 1000 entries of 208 bytes.
                                trace = receive(sock, 208008)
                                assert struct.unpack_from('<II', trace) == (0, 0)
                                assert not any(trace[8:]), 'unused trace bytes must be initialized'
                            sock.sendall(PACKET.pack(14, 0, wire_eid))  # RESUME
                            pending_resumes += 1
                            if eid == 2:
                                assert struct.unpack_from('<i', event, 21)[0] == 0
                                break
                        while pending_resumes:
                            assert PACKET.unpack(receive(sock, PACKET.size))[0] == 0
                            pending_resumes -= 1
                        assert 1 in seen and 8 in seen, seen
                        print('PASS: protocol 9, native TID, registers, memory, trace, image/start/exit events:', seen)
                    else:
                        print('PASS: incompatible protocol rejected with version 9 reply')
                assert proc.wait(timeout=15) == 0, proc.returncode
            except BaseException:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)
                log.seek(0)
                print(log.read())
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pin', required=True)
    parser.add_argument('--tool', required=True)
    parser.add_argument('--app', default='/bin/true')
    parser.add_argument('--event-ids', choices=('legacy', 'modern'),
                        help='Omit to verify the default IDA 8.5-compatible mode')
    parser.add_argument('--bits', type=int, choices=(32, 64), default=64)
    args = parser.parse_args()
    run(args, 1)
    run(args, 9)


if __name__ == '__main__':
    main()
