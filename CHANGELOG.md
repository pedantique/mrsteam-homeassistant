# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

HACS shows the GitHub Release notes in its own interface; this file mirrors them
for anyone browsing the repository directly.

## [Unreleased]

## [0.1.3] - 2026-10-21

### Fixed

- Runtime authentication and connection errors are now handled correctly. When
  the stored credentials stop working during normal operation (for example after
  a password change), Home Assistant now starts the re-authentication flow instead
  of logging a traceback on every poll. AWS and network errors are reported as a
  retryable update failure, and a failed start, stop or program command now shows
  a clear message instead of a raw traceback.

## [0.1.2] - 2026-10-20

### Added

- Re-authentication flow. When the stored credentials are rejected, Home
  Assistant now prompts for the new password, validates it against the API, and
  updates the saved credentials in place, instead of leaving the user to delete
  and re-add the integration.

## [0.1.1] - 2026-09-24

### Added

- Dark-theme brand logo, so the wordmark stays legible on Home Assistant's dark
  theme.

### Changed

- Cleaner brand icon and logo assets, with source compression artefacts removed.
- README: clarified the two-client cloud model, the credentials and privacy
  handling, and a note that the integration has been tested only against the
  author's own unit.

## [0.1.0] - 2026-09-24

### Added

- Initial release.
- Switch to start and stop steam.
- Select to choose a program.
- Sensors for remaining time, session length, steam-head and room temperature,
  and aroma level.
- Binary sensors for steaming (running) and generator water.
- Config flow with sign-in and device selection, plus a poll-interval option.
- HACS and hassfest validation workflow.

[Unreleased]: https://github.com/pedantique/mrsteam-homeassistant/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/pedantique/mrsteam-homeassistant/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/pedantique/mrsteam-homeassistant/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/pedantique/mrsteam-homeassistant/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/pedantique/mrsteam-homeassistant/releases/tag/v0.1.0
