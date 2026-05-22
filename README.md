# AVCONTROL

Local AV control service for the iPad panel and command-line activities.

## System Assumption

- HDMI Output 1 is unused.
- HDMI Output 2 is the active HDMI output.
- Scenes route HDMI inputs 1-4 to Output 2, then set the LS28SE input and startup volume.

## Run Manually

```sh
python3 /Users/roncompton/AVCONTROL/av_proxy.py
```

Open the panel:

```text
http://<mac-ip>:9090/panel
```

Health check:

```text
http://<mac-ip>:9090/health
```

## Run as a Mac Service

Copy or symlink the launchd plist:

```sh
cp /Users/roncompton/AVCONTROL/launchd/com.roncompton.avcontrol.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.roncompton.avcontrol.plist
```

Stop it:

```sh
launchctl unload ~/Library/LaunchAgents/com.roncompton.avcontrol.plist
```

Logs are written to:

```text
/Users/roncompton/AVCONTROL/logs/avcontrol.out.log
/Users/roncompton/AVCONTROL/logs/avcontrol.err.log
```

## Optional Environment Overrides

- `AV_PROXY_PORT`
- `AV_MATRIX_HOST`
- `AV_MATRIX_PORT`
- `AV_PREAMP_HOST`
- `AV_PREAMP_PORT`
- `AV_ITACH_HOST`
- `AV_ITACH_PORT`
- `AV_ACTIVE_HDMI_OUTPUT`
- `AV_START_VOLUME`
