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
  /** The model `default` gives this role (the mode's override applied), also while another model is pinned. */
  default_model?: string
  /** The agent file's `description:` line; the pane shows it when the pointer is on the role (additive, 01/11/2026). */
  description?: string
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
/** `outside`: the session's folder is in no git repository, so no code work happens there (additive, 01/11/2026). */
export type Promotion = { stages: Stage[]; error?: string; outside?: boolean }
/** One row of the session's status table: what it is, where it stands, the measured figure with its signal, what it waits on. */
export type StatusRow = { item: string; state: string; figure: string; waiting: string }
/** The session's status table (scripts/adyusuf_status.py writes it): what runs now, what runs next, the rows. */
export type StatusData = { now: string; next: string; rows: StatusRow[]; updated: string }

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
      /** The session's status table from ~/.claude/adyusuf-status/<session>.json; null when there is none. */
      status: StatusData | null
      /** Which of the pane's boxes are folded, by id (settings, agents, promotion); the pane starts with agents and promotion folded. */
      folded: Record<string, boolean>
    }
  }
}
