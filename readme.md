# Israeli Election Data by Ballot

Notebook for displaying the distribution of votes by Ballot box.

## 2026 election

[`view_2026.ipynb`](view_2026.ipynb) downloads the latest official 26th
Knesset ballot-box export, joins it to the cached polling-place table by
`ברזל`, and displays polling-place Voronoi regions clipped to locality
boundaries. Each ballot box is its own hoverable and clickable region. The
original 2022 results are stored under `2022/` and remain available through
`view.ipynb`.

[![2026 notebook](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/shaielc/Behirot/HEAD?labpath=view_2026.ipynb)

**[View the 2026 results map](https://rawcdn.githack.com/shaielc/Behirot/refs/heads/master/2026/results_map.html)**:
a static page exported from the notebook, with an interactive map and no
kernel needed.

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/shaielc/Behirot/HEAD?labpath=view.ipynb)
[![voila](launch.svg)](https://mybinder.org/v2/gh/shaielc/Behirot/HEAD?urlpath=voila%2Frender%2Fview.ipynb)
