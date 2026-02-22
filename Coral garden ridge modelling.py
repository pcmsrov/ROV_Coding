'''
# User Manual: Coral Garden Ridge Modelling

## 1. Introduction
This interactive Python program creates a 3D model of three connected cuboids (rectangular prisms) that represent a simplified “coral garden ridge”. You can adjust the dimensions of the cuboids using sliders and mark specific vertices with red wireframe cubes to track points of interest. The program uses Matplotlib for 3D visualization and interactive widgets.

## 2. Getting Started
### Requirements
- Python 3.7 or later
- Required libraries: `matplotlib`, `numpy`

Install missing libraries with:
```bash
pip install matplotlib numpy
```

### Running the Program
1. Save the script as, for example, `coral_ridge.py`.
2. Run it from your terminal:
   ```bash
   python coral_ridge.py
   ```
3. A window will open displaying the three cuboids (black edges), vertex labels (red letters), and four sliders below the plot.

## 3. Interface Overview
- **3D Plot Area**: Shows the three cuboids.  
  - **Cuboid 1 (left)**: dimensions `L1 × 30 × h1` (h1 fixed at 15).  
  - **Cuboid 2 (middle)**: dimensions `L2 × 30 × H2` (L2 fixed at 45, H2 = 15 + gap12).  
  - **Cuboid 3 (right)**: dimensions `L3 × 30 × H3` (H3 fixed at 25).  
- **Vertex Labels**: Each vertex is labelled with a red letter (A through V).  
- **Sliders**: Four sliders at the bottom control the variable dimensions.  
- **Text Box**: Below the sliders, a text box allows you to enter vertex names to place red cubes.  
- **Legend**: A small legend in the upper left explains that red wireframe cubes mark selected vertices.

## 4. Controls (Sliders)
| Slider | Controls | Range | Initial |
|--------|----------|-------|---------|
| **L1** | Length of cuboid 1 in the X direction (affects AB, CD, EF, GH) | 0 – 200 | 25 |
| **L3** | Length of cuboid 3 in the X direction (affects JQ, KR, ST, UV) | 0 – 200 | 30 |
| **gap12** | Vertical gap between the top of cuboid 1 and the top of cuboid 2 (affects MF, PG) | 20 – 160 | 35 |
| **gap23** | Vertical gap between the top of cuboid 2 and the top of cuboid 3 (affects NS, OV) | 10 – 150 | 25 |

**Important**: `gap12` and `gap23` are linked so that `gap12 = gap23 + 10`. Moving one slider automatically adjusts the other to maintain this relationship. The second cuboid’s height `H2` is then `15 + gap12`.

## 5. Vertex Selection
You can place a **red wireframe cube** (side length 10) at any vertex to highlight it. The cube is placed **inside** the cuboid containing that vertex, with one corner touching the vertex.

### How to select vertices
- Locate the text box labelled **“Vertices (e.g., A,B,C):”** below the sliders.
- Enter one or more vertex letters separated by commas (spaces are allowed).  
  Example: `A, B, E, S`
- Press **Enter** after typing.
- The plot will update, drawing a red cube at each valid vertex. Invalid entries are ignored and a warning is printed in the console.
- To remove all cubes, clear the text box and press Enter.

### Which vertices belong to which cuboid?
- **Cuboid 1** (left, blue in concept): A, D, E, H, plus F and G? Wait, check: vertices A,B,C,D,E,F,G,H are all on cuboid 1? Actually A,B,C,D are bottom, E,F,G,H are top. So all A–H belong to cuboid 1. But B and C are also part of cuboid 2 (shared). For the cube placement, shared vertices are assigned to cuboid 2 to avoid ambiguity.  
  - **Assigned to cuboid 1**: A, D, E, H, F, G? Wait F and G are on top face of cuboid 1, but they are also connected to M and P. They are still vertices of cuboid 1 only. Let's list:  
    - A, D, E, H are exclusive to cuboid 1.  
    - B, C are shared between cuboid 1 and 2.  
    - F, G are on the top face of cuboid 1 but also connect to cuboid 2 via diagonal connectors; they are vertices of cuboid 1 only.  
  - **Assigned to cuboid 2**: B, C, J, K, M, N, O, P. (B and C are shared but we treat them as part of cuboid 2 for cube placement.)  
  - **Assigned to cuboid 3**: Q, R, S, T, U, V.

If you select a vertex that is shared, the cube will be placed in cuboid 2.

## 6. Legend
A red line in the upper left corner of the plot indicates: **“Selected vertex cube”**. This reminds you that all red wireframe boxes correspond to vertices you have chosen.

## 7. Adjusting the View
- You can **rotate** the 3D plot by clicking and dragging with the mouse.
- **Zoom** using the scroll wheel.
- The axes are scaled equally (aspect ratio 1:1:1) so that a 10‑unit cube appears as a true cube.

## 8. Troubleshooting
| Problem | Solution |
|---------|----------|
| **No plot appears** | Ensure you have installed `matplotlib` and `numpy`. Run the script from a terminal to see any error messages. |
| **Sliders don’t move** | Click on the slider handle and drag. If they are frozen, the script may have crashed; check the console for errors. |
| **Vertex text box does nothing** | After typing, you must press **Enter**. If the vertex name is invalid, a warning is printed in the console. |
| **Cube appears in the wrong cuboid** | Shared vertices (B, C, J, K) are assigned to cuboid 2 to avoid ambiguity. This is intentional. |
| **Cube is not a perfect cube** | If the cuboid is too small in a direction, the cube will be truncated to fit inside. The side length may be less than 10 in that dimension. |

## 9. Notes
- The black edges of the cuboids are drawn with linewidth 5 to simulate ½‑inch pipes (visual only).
- Vertex labels are in red, the same colour as the cubes, but they are distinct (text vs. wireframe).
- The program prints the current total lengths `AQ` and `DR` (which are equal) and the second cuboid height `H2` to the console each time you move a slider. This can be useful for documentation.

## 10. Example Session
1. Start the program. The initial model shows three cuboids.
2. In the text box, type `A, B, K` and press Enter. Three red cubes appear: one at A (in cuboid 1), one at B (in cuboid 2), and one at K (in cuboid 2).
3. Drag the **L1** slider to the right – cuboid 1 lengthens, and the cube at A moves with it, staying inside.
4. Drag the **gap12** slider – cuboid 2 grows taller, and the cube at B rises accordingly.
5. To remove all cubes, clear the text box and press Enter.

Enjoy exploring your coral garden ridge model!

'''

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, TextBox
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib.lines import Line2D

# Fixed heights
h1 = 15.0          # first cuboid height (FB, DC)
H3 = 25.0          # third cuboid height (SJ, KV)

# Fixed length of second cuboid
L2 = 45.0

# Initial values for the four groups
L1_init = 25.0     # AB, CD, EF, GH
L3_init = 30.0     # JQ, KR, ST, UV
gap12_init = 35.0  # MF, PG
gap23_init = 25.0  # NS, OV (must be gap12 - 10)

# Global variable for selected vertices (list of letters)
selected_vertices = []

def compute_points(L1, L3, gap12, gap23):
    # Enforce relationship
    if abs(gap12 - gap23 - 10) > 1e-6:
        gap12 = gap23 + 10
    H2 = h1 + gap12   # second cuboid height
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

# Define edges
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
plt.subplots_adjust(bottom=0.35)

# Initial points
points = compute_points(L1_init, L3_init, gap12_init, gap23_init)

def draw_box(corner1, corner2, color='red', linewidth=3):
    """Draw a wireframe box from corner1 to corner2 (axis-aligned)."""
    x1, y1, z1 = corner1
    x2, y2, z2 = corner2
    v = [
        (x1, y1, z1),
        (x2, y1, z1),
        (x2, y2, z1),
        (x1, y2, z1),
        (x1, y1, z2),
        (x2, y1, z2),
        (x2, y2, z2),
        (x1, y2, z2)
    ]
    edges_box = [
        (0,1), (1,2), (2,3), (3,0),
        (4,5), (5,6), (6,7), (7,4),
        (0,4), (1,5), (2,6), (3,7)
    ]
    for e in edges_box:
        ax.plot3D(*zip(v[e[0]], v[e[1]]), color=color, linewidth=linewidth)

def plot_cuboids(points):
    ax.clear()
    # Draw main structure edges
    for edge in edges:
        p1 = points[edge[0]]
        p2 = points[edge[1]]
        ax.plot3D(*zip(p1, p2), color='black', linewidth=5)

    # Label vertices
    for label, coord in points.items():
        ax.text(*coord, f'  {label}', fontsize=8, color='red')

    # Determine bounds for each cuboid
    L1 = points['B'][0]  # B's x
    L3 = points['Q'][0] - points['J'][0]  # Q.x - J.x
    H2 = points['M'][2]  # M's z
    bounds1 = (0, L1, 0, 30, 0, h1)
    bounds2 = (L1, L1+L2, 0, 30, 0, H2)
    bounds3 = (L1+L2, L1+L2+L3, 0, 30, 0, H3)

    # Map each vertex to its cuboid
    vertex_to_cuboid = {
        'A': 1, 'B': 2, 'C': 2, 'D': 1,
        'E': 1, 'F': 1, 'G': 1, 'H': 1,
        'J': 2, 'K': 2,
        'M': 2, 'N': 2, 'O': 2, 'P': 2,
        'Q': 3, 'R': 3,
        'S': 3, 'T': 3, 'U': 3, 'V': 3
    }

    # Draw cubes for all selected vertices (all red now)
    for vertex in selected_vertices:
        if vertex not in points:
            continue
        vx, vy, vz = points[vertex]
        cuboid = vertex_to_cuboid.get(vertex)
        if cuboid == 1:
            xmin, xmax, ymin, ymax, zmin, zmax = bounds1
        elif cuboid == 2:
            xmin, xmax, ymin, ymax, zmin, zmax = bounds2
        elif cuboid == 3:
            xmin, xmax, ymin, ymax, zmin, zmax = bounds3
        else:
            continue

        def get_dir(val, minv, maxv):
            if abs(val - minv) < 1e-6:
                return '+'
            elif abs(val - maxv) < 1e-6:
                return '-'
            else:
                return None

        dx = get_dir(vx, xmin, xmax)
        dy = get_dir(vy, ymin, ymax)
        dz = get_dir(vz, zmin, zmax)

        if dx == '+':
            x2 = min(vx + 10, xmax)
            x1 = vx
        else:
            x1 = max(vx - 10, xmin)
            x2 = vx

        if dy == '+':
            y2 = min(vy + 10, ymax)
            y1 = vy
        else:
            y1 = max(vy - 10, ymin)
            y2 = vy

        if dz == '+':
            z2 = min(vz + 10, zmax)
            z1 = vz
        else:
            z1 = max(vz - 10, zmin)
            z2 = vz

        # Always red
        draw_box((x1, y1, z1), (x2, y2, z2), color='red')
        ax.scatter(vx, vy, vz, color='red', s=50, zorder=10)

    # Add legend for the red cubes
    legend_elements = [Line2D([0], [0], color='red', lw=2, label='Selected vertex cube')]
    ax.legend(handles=legend_elements, loc='upper left')

    # Axes labels
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Coral garden ridge modelling (fixed first & third heights)')

    # Determine global bounds for display
    xs = [coord[0] for coord in points.values()]
    ys = [coord[1] for coord in points.values()]
    zs = [coord[2] for coord in points.values()]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    margin = 5
    ax.set_xlim(xmin - margin, xmax + margin)
    ax.set_ylim(ymin - margin, ymax + margin)
    ax.set_zlim(zmin - margin, zmax + margin)

    ax.set_xticks(np.arange(0, xmax + 10, 10))
    ax.set_yticks(np.arange(0, 40, 10))
    ax.set_zticks(np.arange(0, max(zs) + 10, 10))

    ax.set_box_aspect((xmax - xmin, ymax - ymin, zmax - zmin))

    plt.draw()

plot_cuboids(points)

# Create sliders
axcolor = 'lightgoldenrodyellow'
ax_L1 = plt.axes([0.2, 0.25, 0.6, 0.03], facecolor=axcolor)
ax_L3 = plt.axes([0.2, 0.21, 0.6, 0.03], facecolor=axcolor)
ax_gap12 = plt.axes([0.2, 0.17, 0.6, 0.03], facecolor=axcolor)
ax_gap23 = plt.axes([0.2, 0.13, 0.6, 0.03], facecolor=axcolor)

sli_L1 = Slider(ax_L1, 'L1 (AB, CD, EF, GH)', 0, 200, valinit=L1_init)
sli_L3 = Slider(ax_L3, 'L3 (JQ, KR, ST, UV)', 0, 200, valinit=L3_init)
sli_gap12 = Slider(ax_gap12, 'gap12 (MF, PG)', 20, 160, valinit=gap12_init)
sli_gap23 = Slider(ax_gap23, 'gap23 (NS, OV)', 10, 150, valinit=gap23_init)

# Text box for vertex selection (multiple allowed)
ax_text = plt.axes([0.2, 0.05, 0.2, 0.05])
text_box = TextBox(ax_text, 'Vertices (e.g., A,B,C): ', initial='')

# Update function with coupled sliders
def update(val):
    global points
    new_gap12 = sli_gap12.val
    new_gap23 = sli_gap23.val
    
    # Enforce gap12 = gap23 + 10
    if abs(new_gap12 - new_gap23 - 10) > 0.1:
        if val == sli_gap12:
            new_gap23 = new_gap12 - 10
            if new_gap23 < 10:
                new_gap23 = 10
                new_gap12 = new_gap23 + 10
            elif new_gap23 > 150:
                new_gap23 = 150
                new_gap12 = new_gap23 + 10
            sli_gap23.set_val(new_gap23)
        elif val == sli_gap23:
            new_gap12 = new_gap23 + 10
            if new_gap12 < 20:
                new_gap12 = 20
                new_gap23 = new_gap12 - 10
            elif new_gap12 > 160:
                new_gap12 = 160
                new_gap23 = new_gap12 - 10
            sli_gap12.set_val(new_gap12)
        else:
            if new_gap12 < new_gap23 + 10:
                new_gap12 = new_gap23 + 10
                sli_gap12.set_val(new_gap12)
            elif new_gap12 > new_gap23 + 10:
                new_gap23 = new_gap12 - 10
                sli_gap23.set_val(new_gap23)
    else:
        new_gap12 = sli_gap12.val
        new_gap23 = sli_gap23.val

    L1 = sli_L1.val
    L3 = sli_L3.val
    points = compute_points(L1, L3, new_gap12, new_gap23)
    plot_cuboids(points)
    AQ = L1 + L2 + L3
    print(f"AQ = {AQ:.1f}, DR = {AQ:.1f}, H2 = {h1+new_gap12:.1f}")

def submit_vertices(text):
    global selected_vertices
    text = text.strip()
    if not text:
        selected_vertices = []
    else:
        parts = [p.strip().upper() for p in text.split(',')]
        valid = []
        for p in parts:
            if p in points:
                valid.append(p)
            else:
                print(f"Invalid vertex: {p}. Ignored.")
        selected_vertices = valid
    plot_cuboids(points)

text_box.on_submit(submit_vertices)

sli_L1.on_changed(update)
sli_L3.on_changed(update)
sli_gap12.on_changed(update)
sli_gap23.on_changed(update)


plt.show()
