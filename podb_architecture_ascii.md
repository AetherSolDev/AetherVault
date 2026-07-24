

                                 ┌───────────────────────────────────┐    ┌───────────────────────┐
                                 │             MainEntry             │    │     AddFeedDialog     │
                                 ├───────────────────────────────────┤    ├───────────────────────┤
                                 │ Parses CLI arguments              │    │ Modal URL input       │
                                 │ Launches TUI or headless commands │    │ Validates and submits │
                                 └───────────────────────────────────┘    └───────────────────────┘
                                                  │ │
                                                  │ └──────────────────────────┐
                                           ┌──────┘                            │
                                           │                                   ▼
                                           │               ┌───────────────────────────────────────┐
                                           ▼               │              DataManager              │
                               ┌──────────────────────┐    ├───────────────────────────────────────┤
                               │       PodbApp        │    │ Loads and saves state JSON            │
                               ├──────────────────────┤    │ Manages feed URL list                 │
                               │ Textual App subclass │    │ Tracks played episodes                │
                               │ Owns CSS styling     │    │ Imports/exports OPML files            │
                               │ Mounts FeedScreen    │    │ Tracks progress & E-tag headers       │
                               └──────────────────────┘    ├───────────────────────────────────────┤
                                           │               │ Caches feed results (instant startup) │
                                           │               └───────────────────────────────────────┘
                                           └──────────────────────┐            ▲
                                                              ┌───┼────────────┤
                                                              │   │            │
                                                              │   ▼            │
                                                   ┌───────────────────────────┼┐
                                                   │         FeedScreen        ││
                                                   ├───────────────────────────┼┤
                                                   │ Lists subscribed feeds    ││
                                                   │ Add, remove, refresh─feeds/│rite progress
                                                   │ Loads from cache on mount  │
                                                   │ Background async refresh   │
                                                   │ OPML import/export         │
                                                   └────────────────┼───────────┘
                                                                 │ ││ │
                                                                 │ └┼┐│
                                                                 │  │││
                                                                 │  │▼│
                     ┌──────────────────────┬────────────────────┴────┴───────────────────────┬───────────────────┐
                     │                      │                  EpisodeScreen                  │                   │
                     │                      ├─────────────────────────────────────────────────┤                   │
                     │                      │ Lists feed episodes                             │                   │
                     ▼                      │ Most recent first, capped at 100                │                   │
  ┌────────────────────────────────────┐    │ Color-coded play/pause indicators               │                   ▼
  │           FetchFeedAsync           │    │ Play, pause, seek, stop via IPC                 │    ┌─────────────────────────────┐
  ├────────────────────────────────────┤    │ Periodic player status polling                  │    │       PathInputDialog       │
  │ aiohttp-based async RSS/Atom fetch │    │ Live progress bar updates from stdout data      │    ├─────────────────────────────┤
  │ Returns structured Episodes list   │◄───│ Unplayed-only filter                            │    │ Modal file-path input       │
  │ Does NOT block event loop          │    │ IPC-not-ready fallback for progress bar         │    │ Used for OPML import/export │
  ├────────────────────────────────────┤    ├─────────────────────────────────────────────────┤    └─────────────────────────────┘
  │ Supports conditional GET (304)     │    │ Inline Unicode-block progress bars (█/░)        │
  └────────────────────────────────────┘    │ Column width adjust via Ctrl+Left/Right (20-80) │
                                            │ Sort by column header click (↑/↓)               │
                                            │ Scrub mode toggle (.)                           │
                                            │ Variable-step seeking (5s/1s)                   │
                                            │ Timeline bar in status bar (╈/░ MM:SS / MM:SS)  │
                                            └─────────────────────────────────────────────────┘
                                                                      │
                                                                  ┌───get_live_progress() 1s
                                                                  │
                                                                  ▼
                                        ┌──────────────────────────────────────────────────┐
                                        │                    MpvPlayer                     │
                                        ├──────────────────────────────────────────────────┤
                                        │ Spawns mpv subprocess                            │
                                        │ Parses exit position via term-status-msg         │
                                        │ _live_position/_live_duration from stdout thread │
                                        │ Progress callback on exit                        │
                                        │ Resume via --start flag                          │
                                        ├──────────────────────────────────────────────────┤
                                        │ IPC socket control (pause/seek/status)           │
                                        │ get_live_progress() for real-time UI reads       │
                                        └──────────────────────────────────────────────────┘
                                        
 
------------------ 
classDiagram
    class MainEntry {
        Parses CLI arguments
        Launches TUI or headless commands
    }
    class PodbApp {
        Textual App subclass
        Owns CSS styling
        Mounts FeedScreen
    }
    class DataManager {
        Loads and saves state JSON
        Manages feed URL list
        Tracks played episodes
        Imports/exports OPML files
        Tracks progress & E-tag headers
        Caches feed results (instant startup)
    }
    class FetchFeedAsync {
        aiohttp-based async RSS/Atom fetch
        Returns structured Episodes list
        Supports conditional GET (304)
        Does NOT block event loop
    }
    class FeedScreen {
        Lists subscribed feeds
        Add, remove, refresh feeds
        Loads from cache on mount
        Background async refresh
        OPML import/export
    }
    class EpisodeScreen {
        Lists feed episodes
        Most recent first, capped at 100
        Inline Unicode-block progress bars (█/░)
        Color-coded play/pause indicators
        Play, pause, seek, stop via IPC
        Periodic player status polling
        Live progress bar updates from stdout data
        Column width adjust via Ctrl+Left/Right (20-80)
        Unplayed-only filter
        Sort by column header click (↑/↓)
        Scrub mode toggle (.)
        Variable-step seeking (5s/1s)
        Timeline bar in status bar (╈/░ MM:SS / MM:SS)
        IPC-not-ready fallback for progress bar
    }
    class AddFeedDialog {
        Modal URL input
        Validates and submits
    }
    class PathInputDialog {
        Modal file-path input
        Used for OPML import/export
    }
    class MpvPlayer {
        Spawns mpv subprocess
        IPC socket control (pause/seek/status)
        Parses exit position via term-status-msg
        _live_position/_live_duration from stdout thread
        get_live_progress() for real-time UI reads
        Progress callback on exit
        Resume via --start flag
    }
    MainEntry --> PodbApp
    MainEntry --> DataManager
    PodbApp --> FeedScreen
    FeedScreen --> DataManager
    FeedScreen --> FetchFeedAsync
    FeedScreen --> EpisodeScreen
    FeedScreen --> PathInputDialog
    EpisodeScreen --> DataManager : read/write progress
    EpisodeScreen --> FetchFeedAsync
    EpisodeScreen --> MpvPlayer : get_live_progress() 1s
