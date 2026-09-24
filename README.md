# MrSteam iSteamX — Home Assistant integration

Control and monitor a **MrSteam iSteamX** steam generator from Home Assistant.

This is an unofficial integration built by reverse-engineering the MrSteam app's
cloud API (AWS Cognito + API Gateway + AWS IoT device shadows). It talks to the
same MrSteam cloud the app uses — no local device API exists.

> ⚠️ **Safety.** Steam generators are powerful appliances. Only automate
> activation when you can be certain the steam room is unoccupied and the door is
> closed. You are responsible for safe use. This project has no affiliation with
> MrSteam / Feel Good Inc.

## Features

- **Switch** — start / stop steam
- **Select** — choose a program (`default`, plus programs you've created in the app)
- **Sensors** — remaining time, session length, steam temperature, room
  temperature, aroma level
- **Binary sensors** — steaming (running), water

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add this repo, category **Integration**.
2. Install **MrSteam iSteamX**, restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → MrSteam iSteamX.**
4. Enter your MrSteam app **email** and **password**. If prompted, pick your
   generator. (Model number defaults to `SU-70`; change it if yours differs.)

## How it works & the one important caveat

MrSteam coordinates controllers at the **device-shadow** level: the wall
control, the phone app, and this integration all read the shadow's *reported*
state and write its *desired* state. The generator reconciles whoever wrote last.

However, the AWS IoT **connection** layer only permits one client using the
required identity (`client_id == thingName`), and your **wall control unit owns
it**. So this integration never holds a persistent connection — it does a quick
*connect → read/command → disconnect* **burst** on each poll and each command,
exactly like the phone app does when you open it.

Practical implications:

- Each poll/command briefly (~2 s) knocks the wall unit off the **cloud** — its
  local operation and any running steam session are **not** affected.
- Increase **Poll interval** (integration Options) to reduce that churn. Default
  is 60 s; minimum 20 s.
- Status in HA can be up to one poll interval stale.

## Notes / known rough edges

- Temperature encodings (`deviceSteamTemp`, `deviceRoomTemp`) are decoded as
  tenths of a degree and reported in the account's unit (°C/°F). Treat them as
  best-effort until validated against your unit — please open an issue with real
  readings if they look off.
- `model_number` is a config field because the app sources it from your account;
  if discovery returns no devices, try your actual model string.

## Credits

Reverse-engineered and built for personal use. Contributions welcome.

## License

MIT
