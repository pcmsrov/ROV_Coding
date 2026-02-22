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