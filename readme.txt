This is a PIN tool that connects IDA Pro's debugger to Intel PIN. IDA can
instrument, trace, suspend and inspect a process, and manage breakpoints.
The tool is distributed as source and must be rebuilt for the host OS and kit.

Supported PIN target
--------------------
Intel PIN 4.4, build 99977, revision g54fbb8814 (Windows and Linux).
Linux kit: pin-external-4.4-99977-g54fbb8814-gcc-linux
Windows: use the corresponding PIN 4.4 clang-windows kit, not the Linux kit.
Both IA-32 and Intel 64 builds are retained. Older PIN compatibility branches
remain where practical, but PIN 3.x is no longer the validation target.
The IDA wire protocol remains version 9. It does not expose APX r16-r31 or
AMX tile registers; this port does not extend IDA's register protocol.

Requirements (from the PIN 4.4 kit)
---------------------------------
Linux: kernel >= 4.12.14; GCC 6.1 through 14 (10 or newer recommended).
Install matching GCC multilib support when building TARGET=ia32.
Windows: Windows 11 23H2+ or Windows Server 2022+; LLVM 15 or 16 (clang-cl
and lld-link), Windows SDK, GNU make and a Cygwin/MinGW-compatible shell.
Microsoft cl.exe is not supported for PIN 4 tools. The kit supports the LLVM
bundled with Visual Studio 2022 17.6; other VS releases' bundled LLVM versions
are outside its supported range. A standalone LLVM 15/16 can also be used.
See the kit's README.md and doc/html/index.html for full platform requirements.

Linux build
-----------
From this directory, set PIN_ROOT to the extracted Linux kit:

  export PIN_ROOT="/path/to/pin-external-4.4-99977-g54fbb8814-gcc-linux"
  make PIN_ROOT="$PIN_ROOT" TARGET=intel64 tools
  make PIN_ROOT="$PIN_ROOT" TARGET=ia32 tools

Outputs: obj-intel64/idadbg64.so and obj-ia32/idadbg.so.
Use DEBUG=1 with a separate OBJDIR (ending in /) for debug builds, for example:

  make PIN_ROOT="$PIN_ROOT" TARGET=intel64 DEBUG=1 OBJDIR=obj-intel64-debug/ tools

To select a GCC version, export PIN_WRAPPER_GCC=/usr/bin/gcc-14 before making.
Keep the kit's TOOL_CXX/TOOL_LINKER wrappers: do not replace them with a host
compiler or link against the host C/C++ runtime. IDA_OBJDIR and IDA_EXTRA_*
flags remain supported; legacy IDA_CC/IDA_CXX/IDA_CCL overrides apply only to
older kits. With PIN 4 use the kit's PIN_WRAPPER_* environment variables.
Clean or use a new OBJDIR after changing kits, compilers or build options.

Windows build
-------------
Open a Visual Studio developer command prompt with the Windows SDK configured.
Put a supported LLVM's clang-cl.exe and lld-link.exe, GNU make, bash and shell
utilities on PATH. Start the Cygwin/MinGW shell from that environment; do not
use WSL's Linux compiler for a Windows build. Use kit paths without spaces.
In that shell, from this directory (adapt the path to your kit):

  export PIN_ROOT=C:/pin/pin-external-4.4-99977-g54fbb8814-clang-windows
  make PIN_ROOT="$PIN_ROOT" TARGET=intel64 tools
  make PIN_ROOT="$PIN_ROOT" TARGET=ia32 tools

Outputs: obj-intel64/idadbg64.dll and obj-ia32/idadbg.dll.
The wrappers select the target architecture. If needed, use the kit variables
PIN_WRAPPER_COMPILER and PIN_WRAPPER_LINKER to select clang-cl and lld-link.

idadbg.sln / idadbg.vcxproj are also usable from VS 2022. The project delegates
to the same GNU make rules instead of maintaining obsolete PIN 3 CRT paths.
Set PIN_ROOT before launching VS, or pass /p:PinRoot=C:/pin/<windows-kit> to
MSBuild. PinBash defaults to bash.exe; override /p:PinBash if needed. Launch
VS/MSBuild with the same developer environment and shell tools on PATH.
Debug/Release and Win32/x64 use separate obj-<target>-<configuration> folders.
There are no developer-specific post-build copy steps.

Running and testing
-------------------
Start the matching tool and application, then connect IDA's PIN debugger:

  "$PIN_ROOT/pin" -t obj-intel64/idadbg64.so -p 23946 -- /path/to/application

On Windows use pin.exe and the corresponding .dll. For IA-32 use idadbg.so
or idadbg.dll. The tool listens for an IDA client; a plain launch waits for
that connection. -idadbg 1 enables diagnostic output.

A Python 3 smoke client is provided; IDA itself is not required:

  python3 tests/smoke.py --pin "$PIN_ROOT/pin" --tool obj-intel64/idadbg64.so

Use --bits 32 and the IA-32 tool for 32-bit testing. --app selects a different
short-lived application that exits successfully (default /bin/true); on
Windows supply an equivalent test .exe. The test checks rejection of old
clients, the v9 handshake, native main-thread IDs, general-register and memory
reads, an empty trace response, image/process events, resume and clean exit.
It binds a temporary local client port and enforces connection/read timeouts.
PIN process instrumentation must be permitted by the host/sandbox policy.
There was no runnable project test suite before this port; generic PIN make
tests cannot supply the required IDA protocol connection.

Port details and validation
---------------------------
- Qualify PIN register names to avoid Pin RT signal-header enum collisions.
- Replace removed PIN_ThreadUid with thread-local listener identification.
- Preserve native OS IDs in IDA events/traces using PIN_GetNativeTid on PIN 4.
- Use Pin RT POSIX sockets on both platforms, including recv (Windows Pin RT
  does not support read on sockets), setsockopt and explicit IPPROTO_TCP.
  Retain legacy WinSock/syscall branches only for older PIN versions.
- Use windows/pinrt_windows.h and libc++ vector::data on PIN 4 Windows.
- Link through TOOL_LINKER and recompile when project headers change.
- Heap-allocate the 208 KiB trace response. The former stack allocation was
  inlined into the packet dispatcher and overflowed PIN 4's listener stack.

Verified on Linux with the supplied PIN 4.4 kit: Intel 64 build, load and
protocol tests with /bin/true and the kit's Utils/hello.c and thread_unix.c
(the latter creates and joins 20 threads). The available host compiler was
GCC 15, outside Intel's documented GCC 6.1-14 range; repeat with supported GCC
for release qualification. IA-32 source compilation succeeded, but linking
was blocked by missing 32-bit GCC crtbeginS.o/crtendS.o; install matching
multilib support before building/running that variant.
Windows source/build paths were reviewed against the kit's Windows rules and
migration guide. No Windows kit/toolchain was available here, so Windows
compilation/runtime testing and a full IDA UI debugging session remain to be
performed on the target systems.

Copyright Hex-Rays 2014-2019
