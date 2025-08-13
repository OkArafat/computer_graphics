import sys
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Window size
WIDTH, HEIGHT = 800, 600


NUM_DROPS = 1200  
RAIN_LENGTH = 20  
RAIN_SPEED = 5    
RAIN_BEND_STEP = 0.3  

# Day/Night parameters
BG_BRIGHTNESS_STEP = 0.01
BG_BRIGHTNESS_MIN = 0.1
BG_BRIGHTNESS_MAX = 1.0

# State variables
rain_drops = []
rain_dx = 1.0  # Rain horizontal speed
bg_brightness = 0.3  # Start with some light
target_brightness = bg_brightness

def init_rain():
    """Initialize rain drops with improved physics"""
    global rain_drops
    rain_drops = []
    
    x_offset = abs(rain_dx) * HEIGHT
    x_min = -x_offset - 100  # Extra buffer for smooth edges
    x_max = WIDTH + x_offset + 100

    for _ in range(NUM_DROPS):
        x = random.uniform(x_min, x_max)
        y = random.uniform(0, HEIGHT + 150) 
      
        life = random.uniform(0.7, 1.0)  # Drop opacity
        speed_var = random.uniform(0.9, 1.1)  # Speed variation
        
        rain_drops.append([x, y, life, speed_var])

def draw_background():
    """Draw sky and ground"""
    # Ground
    glColor3f(0.5, 0.35, 0.1)
    glBegin(GL_TRIANGLES)
    glVertex2f(0, 0)
    glVertex2f(WIDTH, 0)
    glVertex2f(WIDTH, HEIGHT // 2)
    glVertex2f(0, 0)
    glVertex2f(WIDTH, HEIGHT // 2)
    glVertex2f(0, HEIGHT // 2)
    glEnd()
    
    # Sky with day/night cycle
    glColor3f(bg_brightness, bg_brightness, bg_brightness)
    glBegin(GL_TRIANGLES)
    glVertex2f(0, HEIGHT // 2)
    glVertex2f(WIDTH, HEIGHT // 2)
    glVertex2f(WIDTH, HEIGHT)
    glVertex2f(0, HEIGHT // 2)
    glVertex2f(WIDTH, HEIGHT)
    glVertex2f(0, HEIGHT)
    glEnd()

def draw_trees():
    """Draw trees using triangles"""
    num_trees = 13
    tree_base_y = HEIGHT // 2 + 30
    tree_top_y = HEIGHT // 2 + 120
    tree_spacing = WIDTH // num_trees
    tree_base_width = 50
    
    glColor3f(0.0, 1.0, 0.0)  # Green trees
    for i in range(num_trees):
        base_x = i * tree_spacing + (tree_spacing - tree_base_width) // 2
        
        glBegin(GL_TRIANGLES)
        glVertex2f(base_x, tree_base_y)
        glVertex2f(base_x + tree_base_width, tree_base_y)
        glVertex2f(base_x + tree_base_width // 2, tree_top_y)
        glEnd()

def draw_house():
    """Draw the house with all details"""
    house_width = 300
    house_height = 290
    house_left = (WIDTH - house_width) // 2
    house_bottom = (HEIGHT - house_height) // 2
    
    # Ground floor
    glColor3f(0.95, 0.95, 0.92)
    glBegin(GL_TRIANGLES)
    glVertex2f(house_left, house_bottom)
    glVertex2f(house_left + house_width, house_bottom)
    glVertex2f(house_left + house_width, house_bottom + 85)
    glVertex2f(house_left, house_bottom)
    glVertex2f(house_left + house_width, house_bottom + 85)
    glVertex2f(house_left, house_bottom + 85)
    glEnd()

    
    # Second floor
    glColor3f(0.85, 0.78, 0.68)
    glBegin(GL_TRIANGLES)
    glVertex2f(house_left + 20, house_bottom + 85)
    glVertex2f(house_left + house_width - 20, house_bottom + 85)
    glVertex2f(house_left + house_width - 20, house_bottom + 170)
    glVertex2f(house_left + 20, house_bottom + 85)
    glVertex2f(house_left + house_width - 20, house_bottom + 170)
    glVertex2f(house_left + 20, house_bottom + 170)
    glEnd()
    
    # Purple roof
    glColor3f(0.6, 0.4, 0.8)
    glBegin(GL_TRIANGLES)
    glVertex2f(house_left - 30, house_bottom + 170)
    glVertex2f(house_left + house_width + 30, house_bottom + 170)
    glVertex2f(house_left + house_width // 2, house_bottom + 290)
    glEnd()
    
    # Blue door
    glColor3f(0.0, 0.4, 0.8)
    glBegin(GL_TRIANGLES)
    glVertex2f(house_left + 120, house_bottom)
    glVertex2f(house_left + 180, house_bottom)
    glVertex2f(house_left + 180, house_bottom + 50)
    glVertex2f(house_left + 120, house_bottom)
    glVertex2f(house_left + 180, house_bottom + 50)
    glVertex2f(house_left + 120, house_bottom + 50)
    glEnd()
    
    # Doorknob
    glColor3f(0.0, 0.0, 0.0)
    glPointSize(8)
    glBegin(GL_POINTS)
    glVertex2f(house_left + 175, house_bottom + 25)
    glEnd()
    
    # Windows
    window_color = (0.3, 0.6, 0.9)
    
    # Ground floor windows
    for wx in [50, 210]:
        glColor3f(*window_color)
        glBegin(GL_TRIANGLES)
        glVertex2f(house_left + wx, house_bottom + 35)
        glVertex2f(house_left + wx + 40, house_bottom + 35)
        glVertex2f(house_left + wx + 40, house_bottom + 75)
        glVertex2f(house_left + wx, house_bottom + 35)
        glVertex2f(house_left + wx + 40, house_bottom + 75)
        glVertex2f(house_left + wx, house_bottom + 75)
        glEnd()
        
        # Window crosses
        glColor3f(0.0, 0.0, 0.0)
        glLineWidth(2)
        glBegin(GL_LINES)
        glVertex2f(house_left + wx + 20, house_bottom + 35)
        glVertex2f(house_left + wx + 20, house_bottom + 75)
        glVertex2f(house_left + wx, house_bottom + 55)
        glVertex2f(house_left + wx + 40, house_bottom + 55)
        glEnd()
    
    # Second floor windows
    for wx in [70, 190]:
        glColor3f(*window_color)
        glBegin(GL_TRIANGLES)
        glVertex2f(house_left + wx, house_bottom + 105)
        glVertex2f(house_left + wx + 40, house_bottom + 105)
        glVertex2f(house_left + wx + 40, house_bottom + 145)
        glVertex2f(house_left + wx, house_bottom + 105)
        glVertex2f(house_left + wx + 40, house_bottom + 145)
        glVertex2f(house_left + wx, house_bottom + 145)
        glEnd()
        
        # Window crosses
        glColor3f(0.0, 0.0, 0.0)
        glLineWidth(2)
        glBegin(GL_LINES)
        glVertex2f(house_left + wx + 20, house_bottom + 105)
        glVertex2f(house_left + wx + 20, house_bottom + 145)
        glVertex2f(house_left + wx, house_bottom + 125)
        glVertex2f(house_left + wx + 40, house_bottom + 125)
        glEnd()

def draw_rain():
    """Draw rain with improved physics"""
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glLineWidth(2)
    glBegin(GL_LINES)
    
    for drop in rain_drops:
        x, y, life, speed_var = drop
        
       
        rain_r, rain_g, rain_b = 0.6, 0.8, 1.0
   
        alpha = life * max(0.3, 1.0 - (HEIGHT - y) / HEIGHT)
        glColor4f(rain_r, rain_g, rain_b, alpha)
        
        glVertex2f(x, y)
        glVertex2f(x + rain_dx * RAIN_LENGTH, y - RAIN_LENGTH)
    
    glEnd()
    glDisable(GL_BLEND)

def update_rain():
    """Update rain drop positions with better physics"""
    global rain_drops
    
    for drop in rain_drops:
        x, y, life, speed_var = drop
        

        drop[0] += rain_dx * RAIN_SPEED * speed_var
        drop[1] -= RAIN_SPEED * speed_var
      
        drop[2] *= 0.9995
        
        if (drop[1] < -RAIN_LENGTH or 
            drop[0] < -RAIN_LENGTH * abs(rain_dx) - 150 or 
            drop[0] > WIDTH + RAIN_LENGTH * abs(rain_dx) + 150 or
            drop[2] < 0.1):
            
          
            x_offset = abs(rain_dx) * HEIGHT
            drop[0] = random.uniform(-x_offset - 100, WIDTH + x_offset + 100)
            drop[1] = HEIGHT + random.uniform(0, 150)
            drop[2] = random.uniform(0.7, 1.0)
            drop[3] = random.uniform(0.9, 1.1)

def update_brightness():
    """Update background brightness for day/night cycle"""
    global bg_brightness
    if abs(bg_brightness - target_brightness) > 0.001:
        if bg_brightness < target_brightness:
            bg_brightness = min(bg_brightness + BG_BRIGHTNESS_STEP, target_brightness)
        else:
            bg_brightness = max(bg_brightness - BG_BRIGHTNESS_STEP, target_brightness)

def display():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    draw_background()
    draw_trees()
    draw_house()
    draw_rain()
    
    glutSwapBuffers()

def reshape(w, h):
    """Handle window reshape"""
    global WIDTH, HEIGHT
    WIDTH, HEIGHT = w, h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, w, 0, h)
    glMatrixMode(GL_MODELVIEW)

def keyboard(key, x, y):
    """Handle keyboard input"""
    global target_brightness
    key = key.decode('utf-8')
    
    if key == 'n':  
        target_brightness = BG_BRIGHTNESS_MIN
    elif key == 's':  
        target_brightness = BG_BRIGHTNESS_MAX
   
        sys.exit()

def reset_rain_positions():
    """Reset rain positions when direction changes"""
    global rain_drops
    x_offset = abs(rain_dx) * HEIGHT
    x_min = -x_offset - 100
    x_max = WIDTH + x_offset + 100
    
 
    for drop in rain_drops:
        drop[0] = random.uniform(x_min, x_max)
        drop[1] = random.uniform(0, HEIGHT + 150)
        drop[2] = random.uniform(0.7, 1.0)
        drop[3] = random.uniform(0.9, 1.1)

def special_keys(key, x, y):
    """Handle special keys (arrows)"""
    global rain_dx
    
    MAX_TILT = 2.0
    MIN_TILT = -2.0
    
    if key == GLUT_KEY_LEFT:
        rain_dx = max(MIN_TILT, rain_dx - RAIN_BEND_STEP)
        reset_rain_positions()
    elif key == GLUT_KEY_RIGHT:
        rain_dx = min(MAX_TILT, rain_dx + RAIN_BEND_STEP)
        reset_rain_positions()

def idle():
    """Idle function for animation"""
    update_rain()
    update_brightness()
    glutPostRedisplay()

def main():
    """Main function"""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIDTH, HEIGHT)
    glutCreateWindow(b"Rain Direction and Day/Night Simulation - FIXED")
    
 
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    init_rain()
    
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutIdleFunc(idle)
    
    glutMainLoop()

if __name__ == "__main__":
    main()