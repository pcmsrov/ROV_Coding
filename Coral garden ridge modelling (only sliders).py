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