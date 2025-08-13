"""
Catch the Diamonds! - A 2D Game Implementation
==============================================

Author: [Your Name]
Course: Computer Graphics
Assignment: Task-3 - Midpoint Line Drawing Algorithm Implementation

This program implements a simple 2D game called "Catch the Diamonds!" using the
midpoint line drawing algorithm. The game demonstrates the implementation of:
- Eight-zone line drawing using midpoint algorithm
- Zone conversion techniques for handling all line orientations
- AABB collision detection
- Real-time game loop with delta timing
- Interactive UI elements drawn using midpoint lines

Implementation Details:
- All graphics are drawn using only GL_POINTS primitive
- Lines are drawn using the midpoint line drawing algorithm
- Eight-zone symmetry is implemented for drawing lines in any direction
- Game features: diamond catching, scoring, pause/resume, restart, and quit

Educational Purpose: This code is written for educational purposes to demonstrate
the implementation of computer graphics algorithms and game development concepts.

References:
- Midpoint Line Drawing Algorithm (Computer Graphics Theory)
- AABB Collision Detection (Game Development)
- OpenGL/GLUT Framework Documentation
"""

import sys
import random
import time
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# ---------------------------
# Window & Game Parameters
# ---------------------------
WIN_W = 800
WIN_H = 600

score = 0
game_over = False
paused = False

# Catcher
catcher_w = 120
catcher_h = 16
catcher_x = (WIN_W - catcher_w) // 2
catcher_y = 40
catcher_speed = 400
catcher_color = (1.0, 1.0, 1.0)

# Diamond
diamond_size = 28
diamond_x = random.randint(diamond_size, WIN_W - diamond_size)
diamond_y = WIN_H + 50
diamond_speed = 150.0
diamond_color = (1.0, 0.0, 1.0)

# Buttons
button_size = 40
button_padding = 20

def get_button_positions():
    return (
        (button_padding, WIN_H - button_padding - button_size, button_size, button_size),  # restart
        (WIN_W // 2 - button_size // 2, WIN_H - button_padding - button_size, button_size, button_size),  # play
        (WIN_W - button_padding - button_size, WIN_H - button_padding - button_size, button_size, button_size)  # quit
    )

last_frame_time = None
left_pressed = False
right_pressed = False

# ---------------------------
# Utility
# ---------------------------
def log(s):
    print(s)
    sys.stdout.flush()

# ---------------------------
# Midpoint Line Drawing Algorithm Implementation
# ---------------------------
def write_pixel(x, y, color):
    """
    Draw a single pixel at the specified coordinates with the given color.
    This is the fundamental drawing primitive used throughout the program.
    """
    glColor3f(*color)
    glBegin(GL_POINTS)
    glVertex2i(int(x), int(y))
    glEnd()

def find_zone(x1, y1, x2, y2):
    """
    Determine which of the 8 zones a line belongs to based on its slope and direction.
    This is part of the eight-zone symmetry implementation for the midpoint algorithm.
    
    Zone classification:
    Zone 0: 0 <= slope <= 1, left to right
    Zone 1: slope > 1, bottom to top
    Zone 2: slope < -1, top to bottom
    Zone 3: -1 <= slope <= 0, right to left
    Zone 4: 0 <= slope <= 1, right to left
    Zone 5: slope > 1, top to bottom
    Zone 6: slope < -1, bottom to top
    Zone 7: -1 <= slope <= 0, left to right
    """
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) >= abs(dy):
        if dx >= 0 and dy >= 0: return 0
        if dx < 0 and dy >= 0: return 3
        if dx < 0 and dy < 0: return 4
        return 7
    else:
        if dx >= 0 and dy >= 0: return 1
        if dx < 0 and dy >= 0: return 2
        if dx < 0 and dy < 0: return 5
        return 6

def to_zone0(x, y, zone):
    """
    Convert coordinates from any zone to Zone 0 coordinates.
    This transformation allows us to use the Zone 0 midpoint algorithm for all lines.
    """
    if zone == 0: return x, y
    if zone == 1: return y, x
    if zone == 2: return y, -x
    if zone == 3: return -x, y
    if zone == 4: return -x, -y
    if zone == 5: return -y, -x
    if zone == 6: return -y, x
    if zone == 7: return x, -y

def from_zone0(x, y, zone):
    """
    Convert coordinates from Zone 0 back to the original zone.
    This is the inverse transformation of to_zone0().
    """
    if zone == 0: return x, y
    if zone == 1: return y, x
    if zone == 2: return -y, x
    if zone == 3: return -x, y
    if zone == 4: return -x, -y
    if zone == 5: return -y, -x
    if zone == 6: return y, -x
    if zone == 7: return x, -y

def midpoint_line(x1, y1, x2, y2, color=(1,1,1)):
    """
    Draw a line using the midpoint line drawing algorithm with eight-zone support.
    
    This implementation:
    1. Determines the zone of the line
    2. Converts coordinates to Zone 0
    3. Applies the midpoint algorithm for Zone 0
    4. Converts coordinates back to the original zone before drawing
    
    The algorithm uses integer arithmetic for efficiency and handles all line orientations.
    """
    zone = find_zone(x1, y1, x2, y2)
    X1, Y1 = to_zone0(x1, y1, zone)
    X2, Y2 = to_zone0(x2, y2, zone)

    # Ensure we draw from left to right in Zone 0
    if X1 > X2:
        X1, X2 = X2, X1
        Y1, Y2 = Y2, Y1

    # Midpoint algorithm parameters
    dx = X2 - X1
    dy = Y2 - Y1
    d = 2 * dy - dx  # Initial decision parameter
    incE = 2 * dy    # Increment for East step
    incNE = 2 * (dy - dx)  # Increment for North-East step

    x = X1
    y = Y1
    while x <= X2:
        # Convert back to original zone and draw pixel
        ox, oy = from_zone0(x, y, zone)
        write_pixel(ox, oy, color)
        
        # Update decision parameter and coordinates
        if d > 0:
            d += incNE
            y += 1
        else:
            d += incE
        x += 1

def draw_rect(x, y, w, h, color=(1,1,1)):
    midpoint_line(x, y, x+w, y, color)
    midpoint_line(x+w, y, x+w, y+h, color)
    midpoint_line(x+w, y+h, x, y+h, color)
    midpoint_line(x, y+h, x, y, color)

def draw_diamond(cx, cy, size, color=(1,1,1)):
    e = (cx+size, cy)
    n = (cx, cy+size)
    w = (cx-size, cy)
    s = (cx, cy-size)
    midpoint_line(*e, *n, color)
    midpoint_line(*n, *w, color)
    midpoint_line(*w, *s, color)
    midpoint_line(*s, *e, color)

def draw_catcher(x, y, w, h, color=(1,1,1)):
    midpoint_line(x, y, x+w, y, color)
    midpoint_line(x, y, x+w//6, y+h, color)
    midpoint_line(x+w, y, x+w - w//6, y+h, color)
    midpoint_line(x+w//6, y+h, x+w - w//6, y+h, color)

# ---------------------------
# Collision Detection & Game State Management
# ---------------------------
def has_collided(b1, b2):
    """
    AABB (Axis-Aligned Bounding Box) collision detection.
    
    Parameters:
    b1, b2: tuples of (x, y, width, height) representing bounding boxes
    
    Returns:
    True if the boxes overlap, False otherwise
    """
    return (b1[0] < b2[0] + b2[2] and b1[0] + b1[2] > b2[0] and
            b1[1] < b2[1] + b2[3] and b1[1] + b1[3] > b2[1])

def diamond_aabb(x, y, size):
    return (x-size, y-size, size*2, size*2)

def catcher_aabb(x, y, w, h):
    return (x, y, w, h)

def spawn_new_diamond():
    global diamond_x, diamond_y, diamond_color
    diamond_x = random.randint(diamond_size, WIN_W - diamond_size)
    diamond_y = WIN_H + 50
    diamond_color = tuple(max(0.35, random.random()) for _ in range(3))

def reset_game():
    global score, game_over, paused, catcher_x, diamond_speed, catcher_color
    score = 0
    game_over = False
    paused = False
    catcher_x = (WIN_W - catcher_w) // 2
    catcher_color = (1,1,1)
    diamond_speed = 150.0
    spawn_new_diamond()
    log("Starting Over")

# ---------------------------
# Input Callbacks
# ---------------------------
def key_down(key, x, y):
    if key == b'\x1b':
        log(f"Goodbye {score}")
        # Use a more graceful exit method
        import os
        os._exit(0)

def special_down(key, x, y):
    global left_pressed, right_pressed
    if key == GLUT_KEY_LEFT: left_pressed = True
    if key == GLUT_KEY_RIGHT: right_pressed = True

def special_up(key, x, y):
    global left_pressed, right_pressed
    if key == GLUT_KEY_LEFT: left_pressed = False
    if key == GLUT_KEY_RIGHT: right_pressed = False

def mouse_click(button, state, x, y):
    global paused, game_over
    if state != GLUT_DOWN: return
    mx = x
    my = glutGet(GLUT_WINDOW_HEIGHT) - y

    btn_restart_box, btn_play_box, btn_quit_box = get_button_positions()
    rx, ry, rw, rh = btn_restart_box
    px, py, pw, ph = btn_play_box
    qx, qy, qw, qh = btn_quit_box

    if (rx <= mx <= rx+rw) and (ry <= my <= ry+rh):
        reset_game(); return
    if (px <= mx <= px+pw) and (py <= my <= py+ph):
        if not game_over:
            paused = not paused
            log("Paused" if paused else "Resumed")
        return
    if (qx <= mx <= qx+qw) and (qy <= my <= qy+qh):
        log(f"Goodbye {score}")
        # Use a more graceful exit method
        import os
        os._exit(0)



# ---------------------------
# Drawing
# ---------------------------
def draw_buttons():
    btn_restart_box, btn_play_box, btn_quit_box = get_button_positions()
    rx, ry, rw, rh = btn_restart_box
    px, py, pw, ph = btn_play_box
    qx, qy, qw, qh = btn_quit_box

    draw_rect(rx, ry, rw, rh)
    draw_rect(px, py, pw, ph)
    draw_rect(qx, qy, qw, qh)

    # Restart arrow
    color_restart = (0, 0.8, 0.8)
    midpoint_line(rx+28, ry+rh-8, rx+12, ry+rh//2, color_restart)
    midpoint_line(rx+12, ry+rh//2, rx+28, ry+8, color_restart)
    midpoint_line(rx+28, ry+8, rx+28, ry+rh-8, color_restart)

    # Play/Pause
    color_play = (1.0, 0.6, 0.0)
    if paused:
        midpoint_line(px+12, py+8, px+28, py+ph//2, color_play)
        midpoint_line(px+28, py+ph//2, px+12, py+ph-8, color_play)
        midpoint_line(px+12, py+ph-8, px+12, py+8, color_play)
    else:
        midpoint_line(px+12, py+8, px+12, py+ph-8, color_play)
        midpoint_line(px+28, py+8, px+28, py+ph-8, color_play)

    # Quit cross
    color_quit = (0.9, 0.1, 0.1)
    # Draw X shape - diagonal lines
    midpoint_line(qx+8, qy+8, qx+qw-8, qy+qh-8, color_quit)
    midpoint_line(qx+qw-8, qy+8, qx+8, qy+qh-8, color_quit)

def draw_scene():
    glClear(GL_COLOR_BUFFER_BIT)
    draw_buttons()
    if not game_over:
        draw_diamond(int(diamond_x), int(diamond_y), diamond_size//2, diamond_color)
    draw_catcher(int(catcher_x), int(catcher_y), catcher_w, catcher_h, catcher_color)

# ---------------------------
# Game Loop
# ---------------------------
def update_and_render():
    """
    Main game loop function that updates game state and renders the scene.
    Uses delta timing for frame-rate independent movement.
    """
    global last_frame_time, diamond_y, diamond_speed, score, game_over, catcher_x, catcher_color

    # Calculate delta time for frame-rate independent movement
    now = time.time()
    if last_frame_time is None:
        dt = 0
    else:
        dt = now - last_frame_time
    last_frame_time = now

    if not paused and not game_over:
        if left_pressed and not right_pressed:
            catcher_x -= catcher_speed * dt
        if right_pressed and not left_pressed:
            catcher_x += catcher_speed * dt
        catcher_x = max(0, min(WIN_W - catcher_w, catcher_x))

        diamond_y -= diamond_speed * dt
        diamond_speed += 5 * dt

        if has_collided(diamond_aabb(diamond_x, diamond_y, diamond_size),
                        catcher_aabb(catcher_x, catcher_y, catcher_w, catcher_h)):
            score += 1
            log(f"Score: {score}")
            diamond_speed += 15
            spawn_new_diamond()

        if diamond_y + diamond_size < 0:
            game_over = True
            catcher_color = (1, 0, 0)
            log(f"Game Over. Score: {score}")

    draw_scene()
    glutSwapBuffers()

# ---------------------------
# GLUT Setup
# ---------------------------
def reshape(w, h):
    global WIN_W, WIN_H
    WIN_W, WIN_H = w, h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, w, 0, h, -1, 1)
    glMatrixMode(GL_MODELVIEW)

def init_gl():
    glClearColor(0.05, 0.05, 0.12, 1.0)
    glPointSize(1.0)
    glLoadIdentity()
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, WIN_W, 0, WIN_H, -1, 1)
    glMatrixMode(GL_MODELVIEW)

def idle():
    update_and_render()

def main():
    global last_frame_time
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Catch the Diamonds! (Midpoint Lines Only)")
    init_gl()
    glutDisplayFunc(draw_scene)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(key_down)
    glutSpecialFunc(special_down)
    glutSpecialUpFunc(special_up)
    glutMouseFunc(mouse_click)
    glutIdleFunc(idle)
    last_frame_time = time.time()
    spawn_new_diamond()
    glutMainLoop()

if __name__ == "__main__":
    # Start the game
    main()

# End of implementation
# This code demonstrates the practical application of computer graphics algorithms
# in game development, specifically the midpoint line drawing algorithm with
# eight-zone symmetry for handling all line orientations.
