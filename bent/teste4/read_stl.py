import struct
import sys
import os

def read_stl_bounds(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
        
    with open(filepath, 'rb') as f:
        header = f.read(80)
        num_triangles_data = f.read(4)
        if len(num_triangles_data) < 4:
            print("Invalid STL file (too short)")
            return
        num_triangles = struct.unpack('<I', num_triangles_data)[0]
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for _ in range(num_triangles):
            data = f.read(50)
            if len(data) < 50:
                break
            # Struct format: 12 floats (normal + 3 vertices) = 48 bytes, plus 2 bytes attribute
            floats = struct.unpack('<12f', data[:48])
            # Vertices are floats[3:6], floats[6:9], floats[9:12]
            for i in range(1, 4):
                x = floats[i*3]
                y = floats[i*3+1]
                z = floats[i*3+2]
                
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                min_z = min(min_z, z)
                max_z = max(max_z, z)
                
        print(f"STL File: {os.path.basename(filepath)}")
        print(f"  Triangles: {num_triangles}")
        print(f"  X: [{min_x:.6f}, {max_x:.6f}] (diff: {max_x-min_x:.6f})")
        print(f"  Y: [{min_y:.6f}, {max_y:.6f}] (diff: {max_y-min_y:.6f})")
        print(f"  Z: [{min_z:.6f}, {max_z:.6f}] (diff: {max_z-min_z:.6f})")
        print(f"  Center: [{(min_x+max_x)/2:.6f}, {(min_y+max_y)/2:.6f}, {(min_z+max_z)/2:.6f}]")

if __name__ == '__main__':
    folder = "C:\\Antigravity\\IBSimion\\E\\E4\\bent\\teste4"
    for file in os.listdir(folder):
        if file.endswith(".stl"):
            read_stl_bounds(os.path.join(folder, file))
