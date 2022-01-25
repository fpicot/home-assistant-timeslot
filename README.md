# home-assistant-timeslot
A timeslot component for Home Assistant

## Introduction

This component adds a new entity type : the timeslot.
If the current time is between the start and the end of the timeslot, the entity status will be set to True.

This allows for automations that checks if we are inside a timeslot, instead of relying on triggers at the begining and end.

## Example

A simple timeslot that will be configured via the interface
```yaml
timeslot:
  slot1:
```

A full configured timeslot
```yaml
timeslot:
  slot2:
    name: Timeslot with a friendly name
    enabled: True
    start: "07:00"
    end: "09:00"
```
