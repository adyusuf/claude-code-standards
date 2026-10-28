export type Spec = { key: string; type: 'bool' | 'enum'; label: string; group: string; options?: string[] }
export type AgentRow = {
  role: string
  defined: string
  runs_on: string
  active: boolean
  in_mode: boolean
  /** agents.<role>.enabled: auto, on or off */
  enabled: string
  /** agents.<role>.model: default or a model name */
  model: string
}
export type Settings = {
  schema: Spec[]
  values: Record<string, boolean | string>
  sources: Record<string, string>
  /** The user-level defaults (the "Claude settings" block): shipped defaults plus the user's own file, no project or session layer. */
  saved?: { values: Record<string, boolean | string>; sources: Record<string, string> }
  agents: AgentRow[]
}
export type Stage = { branch: string; origin: string; unpushed: number; waived: string[] }
export type Promotion = { stages: Stage[]; error?: string }

declare module 'claude-code' {
  interface PluginState {
    'adyusuf': {
      /** The effective configuration, read through the plugin's own script; null until the first read. */
      settings: Settings | null
      /** Why the settings could not be read (script missing, bad JSON); empty when they could. */
      settingsError: string
      /** Problems the script reports about the configuration files (an unreadable or invalid layer); empty when none. */
      settingsProblems: string[]
      promotion: Promotion | null
      /** Which of the pane's boxes are folded, by id (settings, agents, promotion); the pane starts with agents and promotion folded. */
      folded: Record<string, boolean>
    }
  }
}
