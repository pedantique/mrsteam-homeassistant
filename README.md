# MrSteam iSteamX—Home Assistant integration

Control and monitor a **MrSteam iSteamX** steam generator from Home Assistant.

This is an unofficial integration built by reverse-engineering the MrSteam app's
cloud API (AWS Cognito + API Gateway + AWS IoT device shadows). It talks to the
same MrSteam cloud the app uses—no local device API exists.

_Developed with AI assistance (Claude). Not affiliated with, endorsed by, or
supported by MrSteam / Feel Good Inc._

> ⚠️ **Safety.** Steam generators are powerful appliances. Only automate
> activation when you can be certain the steam room is unoccupied and the door is
> closed. You are responsible for safe use. This project has no affiliation with
> MrSteam / Feel Good Inc.

## Features

- **Switch**—start / stop steam
- **Select**—choose a program (`default`, plus programs you've created in the app)
- **Sensors**—remaining time, session length, steam temperature, room
  temperature, aroma level
- **Binary sensors**—steaming (running), water

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add this repo, category **Integration**.
2. Install **MrSteam iSteamX**, restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → MrSteam iSteamX.**
4. Enter your MrSteam app **email** and **password**. If prompted, pick your
   generator. (Model number defaults to `SU-70`; change it if yours differs.)

### About your credentials

The integration signs in to **MrSteam's own cloud** with your app email and
password (AWS Cognito SRP—the same login the phone app uses) and exchanges them
for short-lived AWS tokens. Your password is sent only to MrSteam's Cognito
endpoint and is stored in Home Assistant's config entry on your own server; it is
not transmitted anywhere else and this project has no server of its own. Because
there is no local device API, cloud sign-in is the only way to reach the unit.

## How it works & the one important caveat

MrSteam coordinates controllers at the **device-shadow** level: the wall
control, the phone app, and this integration all read the shadow's *reported*
state and write its *desired* state. The generator reconciles whoever wrote last.

This integration never holds a persistent connection. It does a quick
*connect → do one thing → disconnect* **burst** for each poll and each command,
exactly like the phone app does when you open it, using two different IoT client
identities:

- **Reads** connect as `client_id == thingName` (the only identity allowed to
  subscribe to the shadow). Your **wall control unit** also uses that identity, so
  a read briefly (~2 s) bumps the wall unit off the **cloud**—its local
  operation and any running steam session are **not** affected.
- **Commands** (start/stop/program) publish from a unique `app-*-dev` client that
  coexists with the wall unit, so sending a command does **not** disturb it.

Practical implications:

- Increase **Poll interval** (integration Options) to reduce the read churn.
  Default is 60 s; minimum 20 s.
- Status in HA can be up to one poll interval stale. After a command the switch
  updates optimistically and a confirming read follows a few seconds later.

## Why this integration exists

This project grew out of independent research into how the MrSteam app talks to
its cloud. It only ever communicates with **your own** account and **your own**
device, using the same access the official app uses.

It has **not** been tested against any hardware other than the author's own unit,
so expect rough edges—please [open an issue](https://github.com/pedantique/mrsteam-homeassistant/issues)
if something misbehaves, ideally with logs and your model number.

## Notes / known rough edges

- Temperature encodings (`deviceSteamTemp`, `deviceRoomTemp`) are decoded as
  tenths of a degree and reported in the account's unit (°C/°F). Treat them as
  best-effort until validated against your unit—please open an issue with real
  readings if they look off.
- `model_number` is a config field because the app sources it from your account;
  if discovery returns no devices, try your actual model string.

## Credits

Reverse-engineered and built for personal use. Contributions welcome.

## License

MIT
