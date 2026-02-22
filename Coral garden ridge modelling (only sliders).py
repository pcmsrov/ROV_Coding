'''
"""
=========================================
Coral Garden Ridge Modelling User Manual
=========================================

This script creates an interactive 3D visualization of three connected cuboids
representing a simplified "coral garden ridge" structure. The cuboids are
arranged in a chain along the X‑axis, sharing faces, with adjustable heights
controlled by two linked sliders.

-------------------------------------------------------------------------------
Model Description
-------------------------------------------------------------------------------
The structure consists of three cuboids:

1. **First cuboid** (blue when drawn – but here all edges are black):
   - Dimensions: X = L1 (front/back length), Y = 30 (fixed), Z = h1 = 15.
   - Vertices: A (origin), B, C, D at bottom; E, F, G, H at top.
   - Fixed edges: AB = L1, DC = L1, FB = h1 (vertical at B), etc.

2. **Second cuboid** (red, but edges black):
   - Dimensions: X = L2 = 45 (fixed), Y = 30 (fixed), Z = H2 (variable).
   - Attached to the right face (BCFG) of the first cuboid.
   - Vertices: B, J, K, C at bottom; M, N, O, P at top.

3. **Third cuboid** (green, but edges black):
   - Dimensions: X = L3 = 30 (initial, but can be changed in code), Y = 30 (fixed), Z = H3 = 25 (fixed).
   - Attached to the right face (NOJK) of the second cuboid.
   - Vertices: J, Q, R, K at bottom; S, T, U, V at top.

Fixed values (hard‑coded):
   L1 = 15          (AB, DC)
   h1 = 15          (FB, vertical edge of first cuboid)
   L2 = 45          (BJ, CK)
   H3 = 25          (SJ, KV – height of third cuboid)
   L3 = 30          (JQ, KR – can be edited in the code)

The variable heights are:
   H2 = h1 + gap12   (height of second cuboid)
   gap12 = H2 - h1   (MF, PG – vertical edges from first to second cuboid)
   gap23 = H2 - H3   (NS, OV – vertical edges from second to third cuboid)

Because H3 and h1 are fixed, gap12 and gap23 are linked by:
   gap12 - gap23 = H3 - h1 = 10.

-------------------------------------------------------------------------------
Interactive Controls
-------------------------------------------------------------------------------
Two sliders appear below the plot:

1. **MF, PG (H2 - h1)** – controls gap12 (the extra height of the second cuboid
   above the first). Range: 10 to 150.

2. **NS, OV (H2 - H3)** – controls gap23 (the height difference between the
   second and third cuboids). Range: 0 to 140.

The sliders are linked: moving one automatically adjusts the other so that
gap12 - gap23 = 10 always holds. The second cuboid's total height H2 changes
accordingly.

-------------------------------------------------------------------------------
How to Use
-------------------------------------------------------------------------------
1. **Run the script**:
   - Make sure you have Python and matplotlib installed.
   - If not, install matplotlib: `pip install matplotlib`
   - Run the script: `python coral_garden.py`

2. **Interact with the sliders**:
   - Drag the slider thumb to change the height of the second cuboid.
   - The plot updates in real time.
   - The printed totals AQ and DR (total length from A to Q and from D to R)
     appear in the console. Note: with L3 fixed, AQ = L1 + L2 + L3 = 15+45+30 = 90.

3. **Explore the 3D view**:
   - Click and drag to rotate the plot.
   - Use the scroll wheel to zoom.
   - Hover over vertices to see their labels (A through V).

4. **Customize fixed parameters** (optional):
   - To change L3, edit the line `L3 = 30.0` near the top.
   - To change L1, h1, L2, or H3, modify their respective assignments.
   - If you change H3, the slider link constant (10) must be updated accordingly.

-------------------------------------------------------------------------------
Vertex Labels
-------------------------------------------------------------------------------
All 22 distinct vertices are labelled with letters A through V:

   A (0,0,0)         B (L1,0,0)        C (L1,30,0)       D (0,30,0)
   E (0,0,h1)        F (L1,0,h1)       G (L1,30,h1)      H (0,30,h1)
   J (L1+L2,0,0)     K (L1+L2,30,0)
   M (L1,0,H2)       N (L1+L2,0,H2)    O (L1+L2,30,H2)   P (L1,30,H2)
   Q (L1+L2+L3,0,0)  R (L1+L2+L3,30,0)
   S (L1+L2,0,H3)    T (L1+L2+L3,0,H3) U (L1+L2+L3,30,H3) V (L1+L2,30,H3)

Note that some vertices are shared between cuboids:
   B and C belong to both first and second cuboids.
   J and K belong to both second and third cuboids.

-------------------------------------------------------------------------------
Troubleshooting
-------------------------------------------------------------------------------
- If the plot does not appear, ensure matplotlib is installed and you are using
  an interactive backend (e.g., in VS Code or a Python IDE that supports plots).
- If the sliders are unresponsive, check that the figure window is not frozen.
- If the console shows errors about `p`, you are using an older version of the
  script; this version is correct.

-------------------------------------------------------------------------------
Enjoy exploring your coral garden ridge model!
"""
'''

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d import Axes3D

# ---------- Fixed parameters ----------
L1 = 15.0          # AB, CD, EF, GH (front/back bottom length) from DC = 15
h1 = 15.0          # FB (height of first cuboid)
L2 = 45.0          # BJ, CK (length of second cuboid)
H3 = 25.0          # SJ, KV (height of third cuboid)
L3 = 30.0          # JQ, KR (length of third cuboid) – kept as initial value

# Initial gaps (must satisfy gap12 - gap23 = H3 - h1 = 10)
gap12_init = 35.0  # MF, PG (H2 - h1)
gap23_init = 25.0  # NS, OV (H2 - H3) → 35 - 25 = 10 ✓

def compute_points(gap12, gap23):
    H2 = h1 + gap12   # also equals H3 + gap23 (enforced by slider link)
    points = {
        'A': (0, 0, 0),
        'B': (L1, 0, 0),
        'C': (L1, 30, 0),
        'D': (0, 30, 0),
        'E': (0, 0, h1),
        'F': (L1, 0, h1),
        'G': (L1, 30, h1),
        'H': (0, 30, h1),
        'J': (L1 + L2, 0, 0),
        'K': (L1 + L2, 30, 0),
        'M': (L1, 0, H2),
        'N': (L1 + L2, 0, H2),
        'O': (L1 + L2, 30, H2),
        'P': (L1, 30, H2),
        'Q': (L1 + L2 + L3, 0, 0),
        'R': (L1 + L2 + L3, 30, 0),
        'S': (L1 + L2, 0, H3),
        'T': (L1 + L2 + L3, 0, H3),
        'U': (L1 + L2 + L3, 30, H3),
        'V': (L1 + L2, 30, H3)
    }
    return points

# Edges (same as before)
edges = [
    ('A','B'), ('B','C'), ('C','D'), ('D','A'),
    ('E','F'), ('F','G'), ('G','H'), ('H','E'),
    ('A','E'), ('B','F'), ('C','G'), ('D','H'),
    ('B','J'), ('J','K'), ('K','C'), ('C','B'),
    ('M','N'), ('N','O'), ('O','P'), ('P','M'),
    ('B','M'), ('J','N'), ('K','O'), ('C','P'),
    ('J','Q'), ('Q','R'), ('R','K'), ('K','J'),
    ('S','T'), ('T','U'), ('U','V'), ('V','S'),
    ('J','S'), ('Q','T'), ('R','U'), ('K','V'),
    ('M','F'), ('P','G'), ('N','S'), ('O','V')
]

# Set up plot
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
plt.subplots_adjust(bottom=0.25)

# Initial points
points = compute_points(gap12_init, gap23_init)

def plot_cuboids(points):
    ax.clear()
    # Draw edges as thick pipes
    for edge in edges:
        p1 = points[edge[0]]
        p2 = points[edge[1]]
        ax.plot3D(*zip(p1, p2), color='black', linewidth=5)

    # Label vertices
    for label, coord in points.items():
        ax.text(*coord, f'  {label}', fontsize=8, color='red')

    # Axes labels
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Coral garden ridge modelling')

    # Set limits based on points
    max_x = max(points['Q'][0], points['R'][0]) + 5
    max_y = 30
    all_z = [coord[2] for coord in points.values()]
    max_z = max(all_z) + 5

    ax.set_xlim(0, max_x)
    ax.set_ylim(0, max_y)
    ax.set_zlim(0, max_z)

    # Set integer ticks
    ax.set_xticks(range(0, int(max_x)+1, 10))
    ax.set_yticks([0, 10, 20, 30])
    ax.set_zticks(range(0, int(max_z)+1, 10))

    # Make the scaling equal (isometric)
    ax.set_box_aspect([max_x, max_y, max_z])

    plt.draw()

plot_cuboids(points)

# Create two linked sliders
axcolor = 'lightgoldenrodyellow'
ax_gap12 = plt.axes([0.2, 0.15, 0.6, 0.03], facecolor=axcolor)
ax_gap23 = plt.axes([0.2, 0.10, 0.6, 0.03], facecolor=axcolor)

sli_gap12 = Slider(ax_gap12, 'MF, PG (H2 - h1)', 10, 150, valinit=gap12_init)
sli_gap23 = Slider(ax_gap23, 'NS, OV (H2 - H3)', 0, 140, valinit=gap23_init)

def update(val):
    # Determine which slider changed
    if val == sli_gap12.val:
        gap12 = sli_gap12.val
        # Maintain gap12 - gap23 = 10
        gap23 = gap12 - 10
        if gap23 < 0:
            gap23 = 0
            gap12 = gap23 + 10
            sli_gap12.set_val(gap12)
        sli_gap23.set_val(gap23)
    else:
        gap23 = sli_gap23.val
        gap12 = gap23 + 10
        if gap12 > 150:
            gap12 = 150
            gap23 = gap12 - 10
            sli_gap23.set_val(gap23)
        sli_gap12.set_val(gap12)

    points = compute_points(gap12, gap23)
    plot_cuboids(points)

sli_gap12.on_changed(update)
sli_gap23.on_changed(update)


plt.show()
