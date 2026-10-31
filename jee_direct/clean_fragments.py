"""Remove small stray ink fragments that touch a crop's border (a neighbour option's label, a clipped letter).
clean(path): label connected ink (grown ~1 pt); blank every component that touches the border and holds < min_frac of the largest component's ink."""
import numpy as np
from PIL import Image
from scipy import ndimage


def clean(path, out=None, min_frac=0.12, grow=5):
    im = Image.open(path).convert("RGB"); arr = np.array(im); a = np.array(im.convert("L")) < 190
    lab, n = ndimage.label(ndimage.binary_dilation(a, structure=np.ones((3, 3)), iterations=grow))
    if n < 2: im.save(out or path); return 0
    ink = ndimage.sum(a, lab, index=range(1, n + 1)); big = ink.max(); H, W = a.shape; removed = 0
    for k in range(1, n + 1):
        if ink[k - 1] >= min_frac * big: continue
        m = lab == k; ys, xs = np.nonzero(m)
        if ys.min() <= 1 or xs.min() <= 1 or ys.max() >= H - 2 or xs.max() >= W - 2: arr[m] = 255; removed += 1
    Image.fromarray(arr).save(out or path); return removed
