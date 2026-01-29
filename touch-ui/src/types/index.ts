// Bank names for pattern organization
export type BankName = 'Ambient' | 'Buildup' | 'Chill' | 'Upbeat'

// Pattern information from backend
export interface PatternInfo {
  name: string
  tags: string[]
  description?: string
  category?: BankName
}

// Pattern slot within a bank
export interface PatternSlot {
  patternIndex: number  // Index in backend's full pattern list
  patternName: string
  tags: string[]
}

// Bank configuration
export interface PatternBank {
  id: BankName
  patterns: PatternSlot[]
}

// Zone brightness state
export interface ZoneBrightness {
  ceiling: number
  perimeter: number
  ambient: number
}

// WebSocket status message (extended with pattern info)
export interface DJHueStatus {
  type: 'status'
  bpm: number
  beat_position: number
  bar: number
  beat_in_bar: number
  pattern_index: number
  pattern_name: string
  palette_name: string | null
  palette_override: boolean
  zone_brightness: ZoneBrightness
  fade_active: boolean
  queue_mode: 0 | 1 | 2
  queued_pattern_index: number | null
  queue_target_bar: number | null
  patterns: PatternInfo[] | string[]  // Can be either format during transition
  palettes: PaletteInfo[]  // Palettes with color previews
}

// Palette with color preview (for future backend extension)
export interface PaletteInfo {
  name: string
  colors?: string[]  // RGB hex colors for preview
}

// WebSocket error message
export interface DJHueError {
  type: 'error'
  message: string
}

// Light configuration types
export interface LightInfo {
  rid: string
  name: string
  index: number
  api_channel: number
  groups: string[]
}

export interface LightConfig {
  type: 'light_config'
  lights: LightInfo[]
  groups: Record<string, number[]>
  light_order: string[]
  custom_groups: Record<string, string[]>
  zones: Record<string, string[]>
}

export interface LightConfigSaved {
  type: 'light_config_saved'
  success: boolean
  message: string
}

// Union of all message types
export type DJHueMessage = DJHueStatus | DJHueError | LightConfig | LightConfigSaved

// WebSocket commands
export type DJHueCommand =
  | { type: 'set_pattern'; index?: number; name?: string }
  | { type: 'set_palette'; name?: string | null }
  | { type: 'flash'; duration_beats?: number }
  | { type: 'tap_tempo' }
  | { type: 'sync' }
  | { type: 'start' }
  | { type: 'stop' }
  | { type: 'get_status' }
  | { type: 'get_light_config' }
  | { type: 'save_light_config'; light_order: string[]; custom_groups: Record<string, string[]>; zones: Record<string, string[]> }
  | { type: 'identify_light'; index: number }
  | { type: 'set_zone_brightness'; zone: 'ceiling' | 'perimeter' | 'ambient'; value: number }
  | { type: 'fade_out' }
  | { type: 'set_queue_mode'; mode: 0 | 1 | 2 }

// Bank tag mappings
export const BANK_TAGS: Record<BankName, string[]> = {
  'Ambient': ['ambient', 'wave', 'chill', 'slow'],
  'Buildup': ['energy', 'flash', 'chase', 'build'],
  'Chill': ['classic', 'rainbow', 'pulse', 'fade'],
  'Upbeat': ['strobe', 'spatial', 'signature', 'fast'],
}

export const BANK_ORDER: BankName[] = ['Ambient', 'Buildup', 'Chill', 'Upbeat']
