# Touch Controller System

> **Purpose**: Documentation for the iPad touch controller system, enabling low-latency remote control of DJ-Hue during live performances.

## Overview

The touch controller provides a **web-based interface** for controlling DJ-Hue from an iPad or any browser. It's designed for live performance with low latency (~13-16ms over USB) and large touch targets.

**Key Features:**
- **Pattern & palette selection** via touch-friendly grids
- **Transport controls** - TAP tempo, SYNC, START/STOP
- **Quick actions** - BLACKOUT, FLASH
- **Real-time status** - BPM, beat indicator, current pattern/palette
- **Low latency** - USB connection for beat-drop precision

---

## Architecture

```
┌─────────────────┐     USB      ┌──────────────────┐    WS     ┌─────────────────┐
│   iPad Safari   │─────────────▶│   Touch Server   │──────────▶│    DJ-Hue       │
│   (React App)   │◀─────────────│   :8080          │◀──────────│    :9876        │
└─────────────────┘              └──────────────────┘           └─────────────────┘
                                                                       │
                                                                       │ MIDI
                                                                       ▼
                                                                   Ableton
```

### Components

**Control Server** (`src/dj_hue/control/server.py`)
- WebSocket server on `localhost:9876`
- Runs inside the main DJ-Hue process
- Direct access to PatternEngine, BeatClock, MIDI output
- Broadcasts status at 10Hz to all connected clients

**Touch Server** (`src/dj_hue/touch/server.py`)
- Separate process on port 8080
- Serves the React frontend (built static files)
- Proxies WebSocket connections to DJ-Hue control server
- Supports multiple simultaneous clients

**React Frontend** (`touch-ui/`)
- Vite + React + TypeScript + Tailwind CSS v4
- Touch-optimized with 60px minimum button size
- Auto-reconnecting WebSocket connection
- Dark theme for stage visibility

---

## WebSocket Protocol

All communication uses JSON over WebSocket.

### Commands (Client → Server)

```typescript
// Pattern selection
{ "type": "set_pattern", "index": 5 }
{ "type": "set_pattern", "name": "Rainbow Chase" }

// Palette selection
{ "type": "set_palette", "name": "fire" }
{ "type": "set_palette", "name": null }  // Clear override, use pattern default

// Quick actions
{ "type": "toggle_blackout" }
{ "type": "flash", "duration_beats": 0.5 }

// Transport (sends MIDI to Ableton)
{ "type": "tap_tempo" }  // MIDI note 61
{ "type": "sync" }       // MIDI note 60 + reset beat position
{ "type": "start" }      // MIDI Start message (0xFA)
{ "type": "stop" }       // MIDI Stop message (0xFC)

// Status request
{ "type": "get_status" }
```

### Status (Server → Client)

Broadcast at 10Hz to all connected clients:

```typescript
{
  "type": "status",
  "bpm": 128.0,
  "beat_position": 12.75,
  "bar": 4,
  "beat_in_bar": 1,           // 1-4
  "pattern_index": 3,
  "pattern_name": "Rainbow Chase",
  "palette_name": "fire",
  "palette_override": true,   // false = using pattern's default
  "blackout": false,
  "patterns": ["Solid", "Chase", "Rainbow Chase", ...],
  "palettes": ["fire", "ice", "neon", ...]
}
```

### Errors

```typescript
{
  "type": "error",
  "message": "Cannot connect to DJ-Hue: Connection refused"
}
```

---

## Usage

### Development Mode

Best for iterating on the UI with hot reload:

```bash
# Terminal 1: DJ-Hue main app (includes control server on :9876)
uv run dj-hue

# Terminal 2: Touch server (proxies WebSocket on :8080)
uv run dj-hue-touch

# Terminal 3: Vite dev server (hot reload on :5173)
cd touch-ui && npm run dev
```

Open http://localhost:5173 in browser.

### Production Mode

For actual performances:

```bash
# Build the React app (outputs to src/dj_hue/touch/static/)
cd touch-ui && npm run build

# Terminal 1: DJ-Hue
uv run dj-hue

# Terminal 2: Touch server (serves built files)
uv run dj-hue-touch
```

Access via http://[your-mac-ip]:8080 on iPad.

### USB Connection (Low Latency)

For iOS 17+ using pymobiledevice3:

```bash
# Install pymobiledevice3
pip install pymobiledevice3

# Start USB tunnel daemon (requires sudo, keep running)
sudo python3 -m pymobiledevice3 remote tunneld

# The tunnel creates a virtual network interface
# Access touch server via the tunnel IP shown
```

For older iOS or simpler setup, WiFi works but with higher latency (30-100ms vs 5-15ms).

---

## Touch Server Options

```bash
uv run dj-hue-touch --help

Options:
  --host HOST          Bind address (default: 0.0.0.0)
  --port PORT          Listen port (default: 8080)
  --djhue-host HOST    DJ-Hue control server host (default: localhost)
  --djhue-port PORT    DJ-Hue control server port (default: 9876)
```

---

## Latency Analysis

| Component | Latency |
|-----------|---------|
| iPad touch event | ~8ms |
| WebSocket send (USB) | ~2-5ms |
| Touch server proxy | ~1ms |
| DJ-Hue processing | ~1ms |
| **Total round-trip** | **~13-16ms** |

For comparison:
- WiFi: 30-100ms+ with potential jitter
- USB tunnel: 5-15ms, consistent

---

## File Structure

```
src/dj_hue/
├── control/
│   ├── __init__.py
│   └── server.py          # WebSocket control server
├── touch/
│   ├── __init__.py
│   ├── server.py          # Touch server + proxy
│   └── static/            # Built React app (generated)
│       ├── index.html
│       └── assets/

touch-ui/                   # React source
├── package.json
├── vite.config.ts
├── tsconfig.json
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── hooks/
    │   └── useWebSocket.ts
    └── components/
        ├── StatusBar.tsx
        ├── PatternGrid.tsx
        ├── PaletteGrid.tsx
        └── Controls.tsx
```

---

## Extending the UI

### Adding New Commands

1. Add command handler in `src/dj_hue/control/server.py`:
   ```python
   elif cmd_type == "my_command":
       # Handle command
       await self._broadcast_status()
   ```

2. Add TypeScript type in `touch-ui/src/hooks/useWebSocket.ts`:
   ```typescript
   export interface DJHueCommand {
     type: '...' | 'my_command'
     // ...
   }
   ```

3. Call from React component:
   ```typescript
   send({ type: 'my_command' })
   ```

### Adding Status Fields

1. Add to `_get_status()` in `control/server.py`
2. Add to `DJHueStatus` interface in `useWebSocket.ts`
3. Use in components

### Building for Production

```bash
cd touch-ui
npm run build   # Outputs to ../src/dj_hue/touch/static/
```

The touch server automatically serves files from this directory.
