"""Compute normalized union alpha bounds for validated overlay frame groups."""

import json
import sys

from PIL import Image


def main():
    groups = json.load(sys.stdin)
    result = {}
    for layer_id, paths in groups.items():
        union = None
        size = None
        for value in paths:
            with Image.open(value) as image:
                if size is None:
                    size = image.size
                elif image.size != size:
                    raise ValueError(f"{layer_id} frames do not share one canvas size")
                alpha = image.getchannel("A") if "A" in image.getbands() else None
                bounds = alpha.getbbox() if alpha is not None else image.getbbox()
            if bounds:
                union = bounds if union is None else (
                    min(union[0], bounds[0]), min(union[1], bounds[1]),
                    max(union[2], bounds[2]), max(union[3], bounds[3]),
                )
        if size and union:
            width, height = size
            result[layer_id] = {
                "x": union[0] / width, "y": union[1] / height,
                "width": (union[2] - union[0]) / width,
                "height": (union[3] - union[1]) / height,
            }
        else:
            result[layer_id] = {"x": 0, "y": 0, "width": 1, "height": 1}
    json.dump(result, sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
