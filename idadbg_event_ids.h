#ifndef IDADBG_EVENT_IDS_H
#define IDADBG_EVENT_IDS_H

#include <stdint.h>

// Protocol 9 is used by clients with two different event-number schemes.
// Internal events use the sequential values from the current IDA SDK;
// IDA 8.5 and older clients use bit values on the wire instead.
const uint32_t IDAPIN_LAST_EVENT = 14;

inline bool idapin_event_to_wire(uint32_t event, bool legacy, uint32_t *wire)
{
  if ( event > IDAPIN_LAST_EVENT )
    return false;
  *wire = legacy && event != 0 ? uint32_t(1) << (event - 1) : event;
  return true;
}

inline bool idapin_event_from_wire(uint64_t wire, bool legacy, uint32_t *event)
{
  if ( !legacy || wire == 0 )
  {
    if ( wire > IDAPIN_LAST_EVENT )
      return false;
    *event = uint32_t(wire);
    return true;
  }
  for ( uint32_t id = 1; id <= IDAPIN_LAST_EVENT; ++id )
  {
    if ( wire == (uint64_t(1) << (id - 1)) )
    {
      *event = id;
      return true;
    }
  }
  return false;
}

#endif
