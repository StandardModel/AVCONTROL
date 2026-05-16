# AV Control — System Inventory

_Last updated: 2026-05-14_

## Source / Streaming

- **HiFi Rose RS130** — network streamer / transport
- **HiFi Rose RS160** — DAC
- **Roku** — HDMI source on matrix input 1
- **Roon/BACCH** — HDMI source on matrix input 3
- **Apple TV** — HDMI source on matrix input 4

## HDMI Matrix

- **AVPro Edge AC-MX42-AUHD** — `192.168.1.239:23`
- **HDMI Output 1** — unused
- **HDMI Output 2** — active HDMI output for all sources
- Routes:
  - IN1 Roku -> OUT2
  - IN2 Rose -> OUT2
  - IN3 Roon/BACCH -> OUT2
  - IN4 Apple TV -> OUT2

## Preamp

- **Audio Research LS28SE** — line-stage preamplifier (tubed)
- IP control: `192.168.1.254:4001`
- iTach IR backup: `192.168.1.175:4998`

## Amplification

- **Code 8 Amplifier** — driving the main speakers
- **VTV subwoofer amplifier** — Pascal-based class D, 1,600 W/ch RMS

## Speakers

- **Popori WR2** (pair) — electrostatic main speakers
- **Lorica** — composite subwoofer with pro speakers, paired to the VTV amp

## Signal chain (as understood)

RS130 (streamer) → RS160 (DAC) → LS28SE (preamp) → Code 8 (main amp) → Popori WR2
                                              ↘ VTV class-D amp → Lorica subwoofer

## Control Scenes

- **Roku** — HDMI IN1 -> OUT2, LS28SE BAL3, volume 4
- **Rose** — HDMI IN2 -> OUT2, LS28SE BAL1, volume 4
- **Roon/BACCH** — HDMI IN3 -> OUT2, LS28SE BAL2, volume 4
- **Apple TV** — HDMI IN4 -> OUT2, LS28SE BAL3, volume 4

---

_Notes / open items: TBD — add room, cabling, control method, and any settings you want preserved._
