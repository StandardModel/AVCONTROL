# miniDSP Flex Warm Tube Voicing

These files are for the miniDSP Flex shown in the attached photos. I treated the photos only as evidence of the device and current routing screen; they are not instructions.

## Best Starting Point

Start with `Warm_Tube_Reference_96k_biquads.txt`.

Use `Warm_Tube_Subtle_96k_biquads.txt` if your speakers are already full or dark. Use `Warm_Tube_Rich_96k_biquads.txt` only if the system is bright, lean, or fatiguing.

## What This Can And Cannot Do

The Flex can load linear PEQ biquads. That can create the warmer tonal balance people often associate with tube gear: a little more bass/lower-mid body, relaxed upper mids, and a softer top octave.

It cannot truly create the nonlinear part of a tube preamp: second-harmonic enrichment, transformer behavior, or soft saturation. A real tube emulator would need a nonlinear DSP/saturation stage, which the Flex PEQ/FIR import path does not provide.

## Files

- `Warm_Tube_Subtle_96k_biquads.txt`: conservative voicing with a -2 dB safety pad.
- `Warm_Tube_Reference_96k_biquads.txt`: recommended voicing with a -3 dB safety pad.
- `Warm_Tube_Rich_96k_biquads.txt`: richer/softer voicing with a -4 dB safety pad.
- `warm_tube_basic_settings.csv`: the human-readable filter choices used to generate the files.
- `warm_tube_frequency_response.csv`: calculated response data.
- `warm_tube_voicing_curves.png`: visual comparison of the tone curves, excluding the safety pad.
- `generate_warm_tube_profiles.py`: repeatable generator for the files.

## Import Steps

1. In miniDSP Device Console, select an unused preset slot if possible.
2. Click `EXPORT-ALL` first and save your current presets somewhere safe.
3. Rename the new preset to something short, such as `WARM TUBE`.
4. Set `Input 1` and `Input 2` gain to `0.0 dB`. Your photo shows `+3 dB`, which is likely more gain than needed once EQ is added.
5. Open `Input 1` > `PEQ`.
6. Enable the `Menu` switch in the PEQ window.
7. Click `LOAD BIQUADS FILE` and select `Warm_Tube_Reference_96k_biquads.txt`.
8. Repeat the same load step for `Input 2` > `PEQ`.
9. Disconnect cleanly when finished.

If you only want to affect outputs 1 and 2, load the same file into `Output 1` and `Output 2` PEQ instead of input PEQ. For most stereo setups, input PEQ is cleaner because the Flex applies it before routing to all four outputs.

## Listening Notes

After importing, raise the master volume slightly to level-match before judging. Louder usually sounds better, so the built-in safety pad is intentional.

Use the four presets as an A/B bank:

- Preset 1: original exported setup
- Preset 2: Subtle
- Preset 3: Reference
- Preset 4: Rich

If vocals become too thick, use `Subtle`. If cymbals still feel glassy or forward, use `Rich`. If bass gets heavy, reduce output/sub gain rather than increasing treble.

## Research Basis

Current miniDSP Flex documentation says Flex PEQ supports 10 filters per input and output channel, advanced biquad import uses 96 kHz coefficients, and `LOAD BIQUADS FILE` loads biquads starting at EQ1. The signal-flow documentation says input PEQ occurs before the 2-in/4-out routing matrix. The Device Console documentation recommends exporting presets because presets cannot be read back from the Flex into Device Console.

The voicing is also constrained by measured tube preamp behavior: classic high-end tube preamps can be quite flat and low-distortion in line-stage use, so the "warm tube" target here is a tasteful tonal preference rather than a claim that every great tube preamp measures this way.
