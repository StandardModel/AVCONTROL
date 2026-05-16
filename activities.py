#!/usr/bin/env python3
"""
Command-line activity launcher for the AV control system.

This uses the same scene definitions as the web service:
- HDMI Output 1 is unused.
- HDMI Output 2 is the active route for every HDMI source.
- LS28SE input and startup volume are applied with each scene.
"""

from __future__ import annotations

from av_proxy import ACTIVE_MATRIX_OUTPUT, SCENES, run_scene


MENU = {
    "1": "rose",
    "2": "roon",
    "3": "roku",
    "4": "apple",
}


def print_menu() -> None:
    print("\nAVAILABLE ACTIVITIES:\n")
    for key, scene_name in MENU.items():
        scene = SCENES[scene_name]
        print(
            f"{key} = {scene['label']} "
            f"(HDMI IN{scene['hdmi']} -> OUT{ACTIVE_MATRIX_OUTPUT}, "
            f"Preamp {scene['preamp']}, Vol {scene['volume']})"
        )
    print("")


def main() -> None:
    print_menu()
    choice = input("Select Activity: ").strip()
    scene_name = MENU.get(choice)

    if not scene_name:
        print("Invalid choice")
        return

    print(f"Running scene: {SCENES[scene_name]['label']}")
    result = run_scene(scene_name)

    print("Done.")
    print(f"Matrix responses: {result['hdmi']['responses']}")
    print(f"Preamp input: {result['preamp_input']['response'].strip()}")
    print(f"Volume: {result['volume']['response'].strip()}")
    print(f"Mute: {result['mute']['response'].strip()}")


if __name__ == "__main__":
    main()
