import sys  # Ei line ta sys module import kore
import random  # Ei line ta random module import kore
import time  # Ei line ta time module import kore
from OpenGL.GL import *  # OpenGL er GL part import kora hocche
from OpenGL.GLUT import *  # OpenGL er GLUT part import kora hocche
from OpenGL.GLU import *  # OpenGL er GLU part import kora hocche

# Global variables  # Ei line ta global variable gulo define korar age comment
points = []  # Shob point er list
freeze = False  # Game freeze ache kina
blinking_active = False  # Blinking cholche kina
blink_phase = 0  # Blink er kon phase e ache
last_blink_toggle_time = 0  # Last blink kobe hoisilo
window_width, window_height = 500, 500  # Window er width o height
point_size = 5.0  # Size of points in pixels  # Point er size

def init():  # Initial setup function
    glClearColor(0.0, 0.0, 0.0, 1.0)  # Black background set kora hocche
    gluOrtho2D(-100, 100, -100, 100)  # Coordinate system set kora hocche

def draw_box():  # Box draw korar function
    glColor3f(1.0, 1.0, 1.0)  # Box er color white set kora hocche
    glBegin(GL_LINE_LOOP)  # Line loop start
    glVertex2f(-100, -100)  # Box er ekta corner
    glVertex2f(100, -100)  # Box er arekta corner
    glVertex2f(100, 100)  # Box er arekta corner
    glVertex2f(-100, 100)  # Box er arekta corner
    glEnd()  # Line loop sesh

def draw_points():  # Shob point draw korar function
    glPointSize(point_size)  # Point size set kora hocche
    glBegin(GL_POINTS)  # Point drawing start
    for point in points:  # Prottek point er jonno
        x, y, color, dx, dy, speed = point  # Point er value gulo ber kora
        if blinking_active and blink_phase == 1:  # Jodi blink cholche o phase 1 hoy
            glColor3f(0.0, 0.0, 0.0)  # Black color set kora hocche
        else:
            r, g, b = color  # Color value gulo ber kora
            glColor3f(r, g, b)  # Point er color set kora hocche
        glVertex2f(x, y)  # Point er position set kora hocche
    glEnd()  # Point drawing sesh

def display():  # Display function
    glClear(GL_COLOR_BUFFER_BIT)  # Screen clear kora hocche
    draw_box()  # Box draw kora hocche
    draw_points()  # Shob point draw kora hocche
    glutSwapBuffers()  # Buffer swap kora hocche

def update_points():  # Point update korar function
    global points, freeze, blinking_active, blink_phase, last_blink_toggle_time  # Global variable gulo use korbo
    current_time = time.time()  # Akhon er time
    
    # Update blink phase if blinking is active  # Jodi blink cholche, phase update koro
    if blinking_active and current_time - last_blink_toggle_time >= 0.5:  # 0.5 sec por por blink
        blink_phase = 1 - blink_phase  # Phase change kora hocche
        last_blink_toggle_time = current_time  # Last blink time update
        glutPostRedisplay()  # Display abar draw koro
    
    # Update point positions if not frozen  # Jodi freeze na thake, point move koro
    if not freeze:  # Freeze na thakle
        for point in points:  # Prottek point er jonno
            x, y, color, dx, dy, speed = point  # Value gulo ber kora
            new_x = x + dx * speed  # Notun x ber kora
            new_y = y + dy * speed  # Notun y ber kora
            
            # Boundary collision handling  # Boundary te lagle direction change
            if new_x > 100 or new_x < -100:  # X boundary cross korle
                dx = -dx  # X direction ulta koro
                new_x = x + dx * speed  # Notun x abar ber koro
            if new_y > 100 or new_y < -100:  # Y boundary cross korle
                dy = -dy  # Y direction ulta koro
                new_y = y + dy * speed  # Notun y abar ber koro
            
            # Update point position and direction  # Point er value update koro
            point[0] = new_x  # X update
            point[1] = new_y  # Y update
            point[3] = dx  # DX update
            point[4] = dy  # DY update
        
        glutPostRedisplay()  # Display abar draw koro

def mouse(button, state, x, y):  # Mouse event handle korar function
    global points, freeze, blinking_active, blink_phase, last_blink_toggle_time  # Global variable gulo use korbo
    
    if freeze:  # Jodi freeze thake
        return  # Kichu korbena
    
    # Convert window coordinates to OpenGL coordinates  # Window theke OpenGL coordinate e convert
    win_x = (x / window_width) * 200 - 100  # X coordinate convert
    win_y = 100 - (y / window_height) * 200  # Y coordinate convert
    
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:  # Right click dile
        # Create a new point with random color and direction  # Notun point create koro
        color = (random.random(), random.random(), random.random())  # Random color
        dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)  # Random direction
        speed = 1.0  # Speed set kora
        points.append([win_x, win_y, color, dx, dy, speed])  # Point add kora
        glutPostRedisplay()  # Display abar draw koro
    
    elif button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:  # Left click dile
        # Toggle blinking mode  # Blinking on/off koro
        blinking_active = not blinking_active  # Blinking toggle
        if blinking_active:  # Jodi blinking on hoy
            blink_phase = 0  # Phase 0 set koro
            last_blink_toggle_time = time.time()  # Last blink time set koro
        glutPostRedisplay()  # Display abar draw koro

def keyboard(key, x, y):  # Keyboard event handle korar function
    global freeze, points  # Global variable use korbo
    
    if key == b' ':  # Spacebar
        freeze = not freeze  # Freeze toggle koro
    glutPostRedisplay()  # Display abar draw koro

def special_keys(key, x, y):  # Special key event handle korar function
    global freeze, points  # Global variable use korbo
    
    if freeze:  # Jodi freeze thake
        return  # Kichu korbena
    
    if key == GLUT_KEY_UP:  # Up arrow
        for point in points:  # Prottek point er jonno
            point[5] *= 1.1  # Speed barai
    elif key == GLUT_KEY_DOWN:  # Down arrow
        for point in points:  # Prottek point er jonno
            point[5] *= 0.9  # Speed komai
    glutPostRedisplay()  # Display abar draw koro

def main():  # Main function
    glutInit(sys.argv)  # GLUT initialize kora hocche
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)  # Display mode set kora hocche
    glutInitWindowSize(window_width, window_height)  # Window size set kora hocche
    glutCreateWindow(b"Amazing Box")  # Window create kora hocche
    init()  # Initial setup call kora hocche
    glutDisplayFunc(display)  # Display function set kora hocche
    glutIdleFunc(update_points)  # Idle function set kora hocche
    glutMouseFunc(mouse)  # Mouse function set kora hocche
    glutKeyboardFunc(keyboard)  # Keyboard function set kora hocche
    glutSpecialFunc(special_keys)  # Special key function set kora hocche
    glutMainLoop()  # Main loop cholbe

if __name__ == "__main__":  # Main file run korle
    main()  # Main function call kora hocche