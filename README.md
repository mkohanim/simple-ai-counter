# Counter

# Counter

A simple counter plugin for IoX/eisy.

## Behavior
- The counter increments by **1 every second**, starting as soon as the plugin starts.
- The counter is a signed 4-byte integer (-2147483648 to 2147483647). It clamps at the limits rather than wrapping.
- **Step Size** (1-18000, default 1) is used by Increment and Decrement. It does not affect the per-second tick.
- **Status**: Running or Stopped.

## Commands
| Command | Effect |
|---|---|
| Start | Resume the per-second counting |
| Stop | Pause the per-second counting |
| Increment | Add the step size to the counter |
| Decrement | Subtract the step size from the counter |
| Set Step Size | Set the step size (1-18000) |

Increment and Decrement work whether the counter is running or stopped.

## Persistence
The counter value and step size are saved to the plugin's `persist/` directory (every 30 seconds, on Stop, on Increment/Decrement/Set Step Size, and on shutdown) and restored on restart. The counter always starts in the Running state after a restart. A hard power loss can lose up to 30 seconds of ticks.
