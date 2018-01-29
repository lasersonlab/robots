// values in mm

width = 19.05 + 39.71; // x
depth = 31.54 + (4.11 * 2); // y
thickness = 6; // z

difference() {
    cube([width, depth, thickness]);
    
    translate([4.11,         4.11,         -2]) cylinder(10, 3, 3, false);
    translate([4.11,         4.11 + 31.54, -2]) cylinder(10, 3, 3, false);
    translate([4.11 + 31.54, 4.11 + 31.54, -2]) cylinder(10, 3, 3, false);
    translate([4.11 + 31.54, 4.11,         -2]) cylinder(10, 3, 3, false);
    
    translate([4.11 + 10.51,         4.11 + 31.54 - 5.59, -2]) cylinder(10, 2.52, 2.52, false);
    translate([4.11 + 10.51 + 10.06, 4.11 + 31.54 - 5.59, -2]) cylinder(10, 2.52, 2.52, false);
    
    hull() {
        translate([39.71, 4.11 + 31.54 - 5.59, -2]) cylinder(10, 2.2, 2.2, false);
        translate([39.71 + 19.05 - 3.5, 4.11 + 31.54 - 5.59, -2]) cylinder(10, 2.2, 2.2, false);
    }
    
    translate([7, 11, -2]) cube([25, 10, 10]);
}
