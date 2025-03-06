import pygame
import pymunk
import pymunk.pygame_util
import math
import sys
import numpy as np
from enum import Enum
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

# Initialize pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1000, 700
FPS = 60
GRAVITY = 981  # 9.81 m/s^2 * 100 for pymunk scale

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (150, 150, 150)
LIGHT_BLUE = (173, 216, 230)
BROWN = (139, 69, 19)

# Mode enum
class Mode(Enum):
    MECHANICS = 1
    ELECTRICITY = 2
    FLUID = 3
    THERMAL = 4

# Material properties
class Material:
    def __init__(self, name, density, friction, elasticity, color, thermal_conductivity=1.0):
        self.name = name
        self.density = density
        self.friction = friction
        self.elasticity = elasticity
        self.color = color
        self.thermal_conductivity = thermal_conductivity
        self.temperature = 20.0  # Room temperature in Celsius

# Define materials
MATERIALS = {
    "Wood": Material("Wood", 0.5, 0.7, 0.4, BROWN, 0.2),
    "Metal": Material("Metal", 1.0, 0.4, 0.5, GRAY, 0.9),
    "Ice": Material("Ice", 0.9, 0.1, 0.9, LIGHT_BLUE, 0.5),
    "Rubber": Material("Rubber", 0.7, 0.9, 0.9, BLACK, 0.1)
}

# Electrical component properties
class ComponentType(Enum):
    WIRE = 1
    BATTERY = 2
    RESISTOR = 3
    BULB = 4
    SWITCH = 5
    CAPACITOR = 6

class ElectricalComponent:
    def __init__(self, component_type, position, rotation=0):
        self.type = component_type
        self.position = position
        self.rotation = rotation
        self.connections = []  # List of connected components
        self.size = (50, 20)  # Default size
        self.value = 0
        self.on = True  # For switches
        self.charge = 0  # For capacitors
        
        # Set properties based on type
        if component_type == ComponentType.BATTERY:
            self.value = 9.0  # 9V battery
            self.size = (40, 20)
        elif component_type == ComponentType.RESISTOR:
            self.value = 100.0  # 100 Ohms
            self.size = (50, 10)
        elif component_type == ComponentType.BULB:
            self.value = 50.0  # 50 Ohms when lit
            self.size = (20, 20)
        elif component_type == ComponentType.CAPACITOR:
            self.value = 0.01  # 0.01 Farads
            self.size = (30, 20)

# Fluid simulation properties
class Particle:
    def __init__(self, position, material="Water"):
        self.position = position
        self.velocity = [0, 0]
        self.material = material
        self.temperature = 20.0  # Temperature in Celsius
        self.size = 3
        
        if material == "Water":
            self.color = BLUE
            self.density = 1.0
        elif material == "Air":
            self.color = WHITE
            self.density = 0.1
        elif material == "Oil":
            self.color = YELLOW
            self.density = 0.8

# Main Physics Sandbox class
class PhysicsSandbox:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("2D Physics Sandbox")
        self.clock = pygame.time.Clock()
        
        # Set up pymunk space
        self.space = pymunk.Space()
        self.space.gravity = (0, GRAVITY)
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)
        
        # Create static boundary walls
        self.create_boundaries()
        
        # Current mode
        self.mode = Mode.MECHANICS
        
        # Mechanics mode variables
        self.objects = []
        self.selected_object = None
        self.selected_material = "Wood"
        self.applying_force = False
        self.force_direction = None
        self.pendulum = None
        self.spring = None
        
        # Electricity mode variables
        self.components = []
        self.wires = []
        self.selected_component = None
        self.dragging_component = False
        self.circuit_solved = False
        self.voltages = {}
        self.currents = {}
        
        # Fluid mode variables
        self.particles = []
        self.obstacles = []
        self.selected_fluid = "Water"
        
        # Thermal mode variables
        self.heat_sources = []
        self.temperature_map = np.ones((WIDTH//10, HEIGHT//10)) * 20  # Room temperature grid
        
        # UI elements
        self.buttons = self.create_buttons()
        self.sliders = self.create_sliders()
        self.graphs = {}
        self.selected_button = None
        
        # Metrics tracking
        self.metrics = {
            "velocity": [],
            "acceleration": [],
            "temperature": [],
            "voltage": [],
            "current": []
        }
        
        # Font
        self.font = pygame.font.SysFont('Arial', 16)
        self.title_font = pygame.font.SysFont('Arial', 24, bold=True)

    def create_boundaries(self):
        # Floor
        floor = pymunk.Segment(self.space.static_body, (0, HEIGHT - 50), (WIDTH, HEIGHT - 50), 5)
        floor.friction = 0.5
        floor.elasticity = 0.5
        
        # Left wall
        left_wall = pymunk.Segment(self.space.static_body, (0, 0), (0, HEIGHT), 5)
        left_wall.friction = 0.5
        left_wall.elasticity = 0.5
        
        # Right wall
        right_wall = pymunk.Segment(self.space.static_body, (WIDTH, 0), (WIDTH, HEIGHT), 5)
        right_wall.friction = 0.5
        right_wall.elasticity = 0.5
        
        # Add to space
        self.space.add(floor, left_wall, right_wall)

    def create_buttons(self):
        buttons = []
        
        # Mode selection buttons
        buttons.append({"rect": pygame.Rect(20, 20, 150, 40), "text": "Mechanics Mode", "action": lambda: self.set_mode(Mode.MECHANICS)})
        buttons.append({"rect": pygame.Rect(20, 70, 150, 40), "text": "Electricity Mode", "action": lambda: self.set_mode(Mode.ELECTRICITY)})
        buttons.append({"rect": pygame.Rect(20, 120, 150, 40), "text": "Fluid Mode", "action": lambda: self.set_mode(Mode.FLUID)})
        buttons.append({"rect": pygame.Rect(20, 170, 150, 40), "text": "Thermal Mode", "action": lambda: self.set_mode(Mode.THERMAL)})
        
        # Material selection buttons
        y_offset = 250
        for material in MATERIALS.keys():
            buttons.append({"rect": pygame.Rect(20, y_offset, 150, 30), "text": material, 
                           "action": lambda m=material: self.set_material(m), "category": "material"})
            y_offset += 40
        
        # Action buttons based on mode
        buttons.append({"rect": pygame.Rect(20, 450, 150, 40), "text": "Add Circle", 
                       "action": self.add_circle, "category": "mechanics"})
        buttons.append({"rect": pygame.Rect(20, 500, 150, 40), "text": "Add Box", 
                       "action": self.add_box, "category": "mechanics"})
        buttons.append({"rect": pygame.Rect(20, 550, 150, 40), "text": "Add Pendulum", 
                       "action": self.add_pendulum, "category": "mechanics"})
        buttons.append({"rect": pygame.Rect(20, 600, 150, 40), "text": "Add Spring", 
                       "action": self.add_spring, "category": "mechanics"})
        
        # Electricity mode buttons
        buttons.append({"rect": pygame.Rect(20, 450, 150, 40), "text": "Add Battery", 
                       "action": lambda: self.add_component(ComponentType.BATTERY), "category": "electricity"})
        buttons.append({"rect": pygame.Rect(20, 500, 150, 40), "text": "Add Resistor", 
                       "action": lambda: self.add_component(ComponentType.RESISTOR), "category": "electricity"})
        buttons.append({"rect": pygame.Rect(20, 550, 150, 40), "text": "Add Bulb", 
                       "action": lambda: self.add_component(ComponentType.BULB), "category": "electricity"})
        buttons.append({"rect": pygame.Rect(20, 600, 150, 40), "text": "Add Switch", 
                       "action": lambda: self.add_component(ComponentType.SWITCH), "category": "electricity"})
        
        # Fluid mode buttons
        buttons.append({"rect": pygame.Rect(20, 450, 150, 40), "text": "Add Water", 
                       "action": lambda: self.set_fluid("Water"), "category": "fluid"})
        buttons.append({"rect": pygame.Rect(20, 500, 150, 40), "text": "Add Oil", 
                       "action": lambda: self.set_fluid("Oil"), "category": "fluid"})
        buttons.append({"rect": pygame.Rect(20, 550, 150, 40), "text": "Add Obstacle", 
                       "action": self.add_obstacle, "category": "fluid"})
        buttons.append({"rect": pygame.Rect(20, 600, 150, 40), "text": "Add Floating Object", 
                       "action": self.add_floating_object, "category": "fluid"})
        
        # Thermal mode buttons
        buttons.append({"rect": pygame.Rect(20, 450, 150, 40), "text": "Add Heat Source", 
                       "action": self.add_heat_source, "category": "thermal"})
        buttons.append({"rect": pygame.Rect(20, 500, 150, 40), "text": "Add Metal Rod", 
                       "action": self.add_thermal_conductor, "category": "thermal"})
        buttons.append({"rect": pygame.Rect(20, 550, 150, 40), "text": "Add Insulator", 
                       "action": self.add_thermal_insulator, "category": "thermal"})
        
        return buttons

    def create_sliders(self):
        sliders = []
        
        # General sliders
        sliders.append({
            "rect": pygame.Rect(190, 20, 150, 20),
            "text": "Gravity",
            "min_value": 0,
            "max_value": 2000,
            "value": GRAVITY,
            "action": self.set_gravity,
            "category": "mechanics"
        })
        
        sliders.append({
            "rect": pygame.Rect(190, 60, 150, 20),
            "text": "Friction",
            "min_value": 0,
            "max_value": 1,
            "value": 0.5,
            "action": self.set_friction,
            "category": "mechanics"
        })
        
        # Electricity sliders
        sliders.append({
            "rect": pygame.Rect(190, 20, 150, 20),
            "text": "Voltage",
            "min_value": 0,
            "max_value": 24,
            "value": 9,
            "action": self.set_voltage,
            "category": "electricity"
        })
        
        sliders.append({
            "rect": pygame.Rect(190, 60, 150, 20),
            "text": "Resistance",
            "min_value": 10,
            "max_value": 1000,
            "value": 100,
            "action": self.set_resistance,
            "category": "electricity"
        })
        
        # Fluid sliders
        sliders.append({
            "rect": pygame.Rect(190, 20, 150, 20),
            "text": "Viscosity",
            "min_value": 0.1,
            "max_value": 10,
            "value": 1,
            "action": self.set_viscosity,
            "category": "fluid"
        })
        
        sliders.append({
            "rect": pygame.Rect(190, 60, 150, 20),
            "text": "Flow Rate",
            "min_value": 1,
            "max_value": 50,
            "value": 10,
            "action": self.set_flow_rate,
            "category": "fluid"
        })
        
        # Thermal sliders
        sliders.append({
            "rect": pygame.Rect(190, 20, 150, 20),
            "text": "Temperature",
            "min_value": -20,
            "max_value": 500,
            "value": 100,
            "action": self.set_temperature,
            "category": "thermal"
        })
        
        sliders.append({
            "rect": pygame.Rect(190, 60, 150, 20),
            "text": "Conductivity",
            "min_value": 0.1,
            "max_value": 1,
            "value": 0.5,
            "action": self.set_conductivity,
            "category": "thermal"
        })
        
        return sliders

    def set_mode(self, mode):
        self.mode = mode
        # Clear specific mode elements if needed
        if mode == Mode.MECHANICS:
            # Reset space with boundary walls
            self.space = pymunk.Space()
            self.space.gravity = (0, GRAVITY)
            self.create_boundaries()
            self.objects = []
        elif mode == Mode.ELECTRICITY:
            self.components = []
            self.wires = []
            self.circuit_solved = False
        elif mode == Mode.FLUID:
            self.particles = []
            self.obstacles = []
        elif mode == Mode.THERMAL:
            self.heat_sources = []
            self.temperature_map = np.ones((WIDTH//10, HEIGHT//10)) * 20

    def set_material(self, material):
        self.selected_material = material

    def set_fluid(self, fluid):
        self.selected_fluid = fluid

    def add_circle(self):
        material = MATERIALS[self.selected_material]
        radius = 20
        mass = math.pi * radius * radius * material.density
        
        # Create body and shape
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = (WIDTH//2, HEIGHT//3)
        shape = pymunk.Circle(body, radius)
        shape.friction = material.friction
        shape.elasticity = material.elasticity
        
        # Store additional properties
        shape.color = material.color
        shape.temperature = material.temperature
        
        # Add to space and object list
        self.space.add(body, shape)
        self.objects.append({"body": body, "shape": shape, "type": "circle", "material": self.selected_material})

    def add_box(self):
        material = MATERIALS[self.selected_material]
        size = (40, 40)
        mass = size[0] * size[1] * material.density
        
        # Create body and shape
        moment = pymunk.moment_for_box(mass, size)
        body = pymunk.Body(mass, moment)
        body.position = (WIDTH//2, HEIGHT//3)
        shape = pymunk.Poly.create_box(body, size)
        shape.friction = material.friction
        shape.elasticity = material.elasticity
        
        # Store additional properties
        shape.color = material.color
        shape.temperature = material.temperature
        
        # Add to space and object list
        self.space.add(body, shape)
        self.objects.append({"body": body, "shape": shape, "type": "box", "material": self.selected_material})

    def add_pendulum(self):
        # Create a fixed pivot point
        pivot = pymunk.Body(body_type=pymunk.Body.STATIC)
        pivot.position = (WIDTH // 2, 100)
        
        # Create pendulum bob
        material = MATERIALS[self.selected_material]
        radius = 20
        mass = math.pi * radius * radius * material.density
        
        bob = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, radius))
        bob.position = (WIDTH // 2, 250)
        
        bob_shape = pymunk.Circle(bob, radius)
        bob_shape.friction = material.friction
        bob_shape.elasticity = material.elasticity
        bob_shape.color = material.color
        
        # Create constraint
        joint = pymunk.PinJoint(pivot, bob, (0, 0), (0, 0))
        
        # Add to space
        self.space.add(bob, bob_shape, joint)
        
        # Store for reference
        self.pendulum = {"pivot": pivot, "bob": bob, "joint": joint, "bob_shape": bob_shape}
        self.objects.append({"body": bob, "shape": bob_shape, "type": "pendulum_bob", "material": self.selected_material})

    def add_spring(self):
        # Create fixed anchor
        anchor = pymunk.Body(body_type=pymunk.Body.STATIC)
        anchor.position = (WIDTH // 2, 100)
        
        # Create movable weight
        material = MATERIALS[self.selected_material]
        size = (40, 40)
        mass = size[0] * size[1] * material.density
        
        weight = pymunk.Body(mass, pymunk.moment_for_box(mass, size))
        weight.position = (WIDTH // 2, 250)
        
        weight_shape = pymunk.Poly.create_box(weight, size)
        weight_shape.friction = material.friction
        weight_shape.elasticity = material.elasticity
        weight_shape.color = material.color
        
        # Create spring constraint
        stiffness = 1000.0
        damping = 100.0
        rest_length = 100.0
        spring = pymunk.DampedSpring(anchor, weight, (0, 0), (0, 0), rest_length, stiffness, damping)
        
        # Add to space
        self.space.add(weight, weight_shape, spring)
        
        # Store for reference
        self.spring = {"anchor": anchor, "weight": weight, "spring": spring, "weight_shape": weight_shape}
        self.objects.append({"body": weight, "shape": weight_shape, "type": "spring_weight", "material": self.selected_material})

    def add_component(self, component_type):
        # Create a new electrical component
        component = ElectricalComponent(component_type, (WIDTH // 2, HEIGHT // 2))
        self.components.append(component)
        self.selected_component = component

    def add_obstacle(self):
        # Add obstacle for fluid simulation
        obstacle = {"rect": pygame.Rect(WIDTH // 2 - 50, HEIGHT // 2, 100, 20), "rotation": 0}
        self.obstacles.append(obstacle)

    def add_floating_object(self):
        # Add a floating object to the fluid simulation
        material = MATERIALS[self.selected_material]
        floating_obj = {
            "rect": pygame.Rect(WIDTH // 2 - 20, HEIGHT // 3, 40, 40),
            "velocity": [0, 0],
            "material": self.selected_material,
            "density": material.density,
            "rotation": 0,
            "angular_velocity": 0
        }
        self.obstacles.append(floating_obj)

    def add_heat_source(self):
        # Create a heat source for thermal simulation
        heat_source = {
            "position": (WIDTH // 2, HEIGHT // 2),
            "radius": 30,
            "temperature": 200.0,
            "power": 50.0
        }
        self.heat_sources.append(heat_source)

    def add_thermal_conductor(self):
        # Add a metal rod or other thermal conductor
        material = "Metal"
        conductor = {
            "rect": pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 10, 200, 20),
            "material": material,
            "temperature": 20.0,
            "conductivity": MATERIALS[material].thermal_conductivity
        }
        self.heat_sources.append(conductor)

    def add_thermal_insulator(self):
        # Add a thermal insulator
        material = "Wood"
        insulator = {
            "rect": pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 10, 200, 20),
            "material": material,
            "temperature": 20.0,
            "conductivity": MATERIALS[material].thermal_conductivity
        }
        self.heat_sources.append(insulator)

    # Slider adjustment functions
    def set_gravity(self, value):
        self.space.gravity = (0, value)

    def set_friction(self, value):
        for obj in self.objects:
            obj["shape"].friction = value

    def set_voltage(self, value):
        for component in self.components:
            if component.type == ComponentType.BATTERY:
                component.value = value

    def set_resistance(self, value):
        for component in self.components:
            if component.type == ComponentType.RESISTOR:
                component.value = value

    def set_viscosity(self, value):
        # Adjust fluid viscosity
        pass

    def set_flow_rate(self, value):
        # Adjust fluid flow rate
        pass

    def set_temperature(self, value):
        for heat_source in self.heat_sources:
            heat_source["temperature"] = value

    def set_conductivity(self, value):
        for heat_source in self.heat_sources:
            if "conductivity" in heat_source:
                heat_source["conductivity"] = value

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Mouse button down
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                # Check UI buttons first
                for button in self.buttons:
                    if "category" not in button or button["category"] == self.mode.name.lower() or button["category"] == "material":
                        if button["rect"].collidepoint(mouse_pos):
                            button["action"]()
                            self.selected_button = button
                            return
                
                # Check sliders
                for slider in self.sliders:
                    if slider["category"] == self.mode.name.lower():
                        if slider["rect"].collidepoint(mouse_pos):
                            # Calculate value based on mouse position
                            ratio = (mouse_pos[0] - slider["rect"].x) / slider["rect"].width
                            value = slider["min_value"] + ratio * (slider["max_value"] - slider["min_value"])
                            value = max(slider["min_value"], min(slider["max_value"], value))
                            slider["value"] = value
                            slider["action"](value)
                            return
                
                # Handle based on current mode
                if self.mode == Mode.MECHANICS:
                    self.handle_mechanics_click(mouse_pos)
                elif self.mode == Mode.ELECTRICITY:
                    self.handle_electricity_click(mouse_pos)
                elif self.mode == Mode.FLUID:
                    self.handle_fluid_click(mouse_pos)
                elif self.mode == Mode.THERMAL:
                    self.handle_thermal_click(mouse_pos)
            
            # Mouse button up
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.mode == Mode.MECHANICS:
                    if self.selected_object:
                        self.selected_object = None
                    self.applying_force = False
                elif self.mode == Mode.ELECTRICITY:
                    self.dragging_component = False
                    self.selected_component = None
            
            # Mouse motion
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = pygame.mouse.get_pos()
                
                # Handle mouse motion based on mode
                if self.mode == Mode.MECHANICS:
                    self.handle_mechanics_motion(mouse_pos)
                elif self.mode == Mode.ELECTRICITY:
                    self.handle_electricity_motion(mouse_pos)
                
                # Check sliders
                for slider in self.sliders:
                    if slider["category"] == self.mode.name.lower():
                        if pygame.mouse.get_pressed()[0] and slider["rect"].collidepoint(mouse_pos):
                            # Calculate value based on mouse position
                            ratio = (mouse_pos[0] - slider["rect"].x) / slider["rect"].width
                            value = slider["min_value"] + ratio * (slider["max_value"] - slider["min_value"])
                            value = max(slider["min_value"], min(slider["max_value"], value))
                            slider["value"] = value
                            slider["action"](value)
                            return
                            
            # Key events
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_r:
                    # Reset current mode
                    self.set_mode(self.mode)
                elif event.key == pygame.K_1:
                    self.set_mode(Mode.MECHANICS)
                elif event.key == pygame.K_2:
                    self.set_mode(Mode.ELECTRICITY)
                elif event.key == pygame.K_3:
                    self.set_mode(Mode.FLUID)
                elif event.key == pygame.K_4:
                    self.set_mode(Mode.THERMAL)

    def handle_mechanics_click(self, mouse_pos):
        # Check for object selection
        for obj in self.objects:
            if self.point_in_shape(mouse_pos, obj["body"], obj["shape"]):
                self.selected_object = obj
                return
        
        # If right mouse button, apply force
        if pygame.mouse.get_pressed()[2]:
            self.applying_force = True
            self.force_start_pos = mouse_pos
    
    def handle_mechanics_motion(self, mouse_pos):
        # Move selected object
        if self.selected_object and pygame.mouse.get_pressed()[0]:
            self.selected_object["body"].position = mouse_pos
            self.selected_object["body"].velocity = (0, 0)
        
        # Update force direction
        if self.applying_force:
            self.force_direction = (mouse_pos[0] - self.force_start_pos[0], 
                                   mouse_pos[1] - self.force_start_pos[1])

    def handle_electricity_click(self, mouse_pos):
        # Check for component selection
        for component in self.components:
            rect = pygame.Rect(component.position[0] - component.size[0]//2,
                              component.position[1] - component.size[1]//2,
                              component.size[0], component.size[1])
            if rect.collidepoint(mouse_pos):
                self.selected_component = component
                self.dragging_component = True
                
                # Toggle switch if clicking on a switch
                if component.type == ComponentType.SWITCH:
                    component.on = not component.on
                return

    def handle_electricity_motion(self, mouse_pos):
        # Move selected component
        if self.dragging_component and self.selected_component:
            self.selected_component.position = mouse_pos

    def handle_fluid_click(self, mouse_pos):
        # Add fluid particles
        if pygame.mouse.get_pressed()[0]:
            for _ in range(5):  # Add multiple particles at once
                offset_x = random.randint(-10, 10)
                offset_y = random.randint(-10, 10)
                particle_pos = (mouse_pos[0] + offset_x, mouse_pos[1] + offset_y)
                self.particles.append(Particle(particle_pos, self.selected_fluid))

    def handle_thermal_click(self, mouse_pos):
        # Add heat at the clicked location
        for heat_source in self.heat_sources:
            if "position" in heat_source and "radius" in heat_source:
                dist = math.sqrt((mouse_pos[0] - heat_source["position"][0])**2 + 
                                (mouse_pos[1] - heat_source["position"][1])**2)
                if dist < heat_source["radius"]:
                    heat_source["temperature"] += 10
            elif "rect" in heat_source:
                rect = pygame.Rect(heat_source["rect"])
                if rect.collidepoint(mouse_pos):
                    heat_source["temperature"] += 10
def point_in_shape(self, point, body, shape):
    if isinstance(shape, pymunk.Circle):
        # For circles, check distance from center
        cx, cy = body.position
        dx = point[0] - cx
        dy = point[1] - cy
        return (dx*dx + dy*dy) <= shape.radius * shape.radius
    elif isinstance(shape, pymunk.Poly):
        # For polygons, check if the point is inside the shape
        vertices = shape.get_vertices()
        return self.point_in_polygon(point, vertices)
    return False

def point_in_polygon(self, point, vertices):
    # Ray casting algorithm to determine if a point is inside a polygon
    x, y = point
    n = len(vertices)
    inside = False
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if y > min(y1, y2):
            if y <= max(y1, y2):
                if x <= max(x1, x2):
                    if y1 != y2:
                        xinters = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                    if y1 == y2 or x <= xinters:
                        inside = not inside
    return inside
