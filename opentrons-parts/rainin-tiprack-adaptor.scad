outer_length = 128;
outer_width = 86;
outer_height = 10;

inner_length = 119;
inner_width = 82.5;
bottom_thickness = 2;

cutout_length = 89;
cutout_width = 52.5;

corner_radius = 4;

cyl_x_offset = outer_length / 2 - corner_radius;
cyl_y_offset = outer_width / 2 - corner_radius;

difference() {
    hull () {
        translate([ cyl_x_offset,  cyl_y_offset, 0]) cylinder(outer_height, corner_radius, corner_radius);
        translate([-cyl_x_offset,  cyl_y_offset, 0]) cylinder(outer_height, corner_radius, corner_radius);
        translate([ cyl_x_offset, -cyl_y_offset, 0]) cylinder(outer_height, corner_radius, corner_radius);
        translate([-cyl_x_offset, -cyl_y_offset, 0]) cylinder(outer_height, corner_radius, corner_radius);
    }
    translate([0, 0, 12]) cube([119, 82.5, 20], center=true);
    cube([89, 52.5, 30], center=true);
}
