'''
要把圖片加載到program 同一file
### 下面有圖片: 按次序
1.png
2.png
3.png
4.png
5.png
background.png
'''
#lib needed
#pip install PyQt6
#pip install matplotlib 

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit
from PyQt6.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Years for the animation
years = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

# Map background images corresponding to each year
background_images = {
    2016: "background.png",
    2017: "1.png",
    2018: "1.png",
    2019: "2.png",
    2020: "2.png",
    2021: "4.png",
    2022: "4.png",
    2023: "4.png",
    2024: "5.png",
    2025: "5.png",
}

# Background image dimensions (resized to half)
BACKGROUND_WIDTH = 425  # Half of 850
BACKGROUND_HEIGHT = 620  # Half of 1241
BACKGROUND_ASPECT_RATIO = BACKGROUND_WIDTH / BACKGROUND_HEIGHT


class CarpMovementModel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Invasive Carp Movement Model")
        self.setGeometry(100, 100, int(BACKGROUND_WIDTH), int(BACKGROUND_HEIGHT))  # Convert dimensions to int

        # Default animation interval (in milliseconds)
        self.animation_interval = 1000  # 1 second

        # Main widget
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        layout = QVBoxLayout(self.main_widget)

        # Year display (move this to the top of the layout)
        self.year_label = QLabel("Year: 2016")
        self.year_label.setStyleSheet("font-size: 16px; font-weight: bold; text-align: center;")
        layout.addWidget(self.year_label)

        # Map display
        self.figure, self.ax = plt.subplots(figsize=(4.25, 6.2))  # Half the original size
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Control buttons and interval input
        self.start_button = QPushButton("Start Animation")
        self.start_button.clicked.connect(self.start_animation)
        layout.addWidget(self.start_button)

        self.interval_input = QLineEdit()
        self.interval_input.setPlaceholderText("Enter interval (ms, e.g., 1000)")
        self.interval_input.setToolTip("Set the time interval between frames in milliseconds.")
        layout.addWidget(self.interval_input)

        # Timer for animation
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_map)
        self.current_year_index = 0

        # Initialize map
        self.draw_map(years[0])  # Start with the first year's map

    def draw_map(self, year):
        """Draw the Illinois River map for a specific year."""
        self.ax.clear()

        # Add resized background image
        try:
            img = mpimg.imread(background_images[year])
            self.ax.imshow(img, extent=[0, BACKGROUND_WIDTH, 0, BACKGROUND_HEIGHT], aspect='auto')  # Fit map to axes
        except FileNotFoundError:
            print(f"Error: Background image for year {year} not found.")

        self.ax.set_title("Illinois River Basin - Invasive Carp Movement")
        self.ax.set_xlim(0, BACKGROUND_WIDTH)
        self.ax.set_ylim(0, BACKGROUND_HEIGHT)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.canvas.draw()

    def start_animation(self):
        """Start the animation."""
        # Set custom interval if provided
        try:
            interval = int(self.interval_input.text())
            if interval > 0:
                self.animation_interval = interval
            else:
                raise ValueError
        except ValueError:
            print("Invalid interval entered. Using default interval of 1000ms.")
            self.animation_interval = 1000  # Default to 1 second

        self.current_year_index = 0
        self.timer.start(self.animation_interval)  # Use the updated interval

    def update_map(self):
        """Update the map for the current year."""
        if self.current_year_index >= len(years):
            self.timer.stop()
            return

        current_year = years[self.current_year_index]
        self.year_label.setText(f"Year: {current_year}")

        # Update the map background for the current year
        self.draw_map(current_year)

        self.current_year_index += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CarpMovementModel()
    window.show()
    sys.exit(app.exec())