// clip_design.scad — frictionless, self-centering transfer clip for the
// smart-fridge scale (1 kg bar load cell). Open in OpenSCAD (free,
// openscad.org) -> F5 preview, F6 render, then File > Export > STL.
//
// Design intent:
//  * SWIVEL PIVOT up top: clip spins/tilts freely so no side-torque reaches
//    the load cell — the "frictionless transfer".
//  * WIDE-MOUTH HOOK: one-handed hang, like a carabiner.
//  * 90° V-SADDLE at the bottom of the hook: items self-center to the same
//    spot every time -> repeatable readings.
//  * Print in PETG (fridge-safe, tough). 1 kg load is trivial for PETG at
//    these sections. The pivot pin can be an M3 bolt.
//
// All key dims are parameters — tweak and re-render.

$fn = 64;

/* ---------- parameters (mm) ---------- */
wire_d      = 9;     // thickness of the hook "wire" body
mouth_gap   = 38;    // opening width — fits jar necks / bag handles
hook_r      = 42;    // main hook inner radius
saddle_w    = 40;    // V-saddle width
saddle_ang  = 90;    // V included angle
eye_id      = 8;     // top eye inner diameter (hangs on M4 eyebolt)
eye_wall    = 4;
pivot_d     = 3.2;   // M3 clearance for the swivel pin
body_t      = 12;    // out-of-plane thickness (side-view width)
gate        = true;  // include spring-gate stub (print TPU or use rubber band)

/* ---------- top eye + swivel housing ---------- */
module eye() {
    difference() {
        union() {
            // eye ring
            translate([0, 0, 0])
                rotate([90, 0, 0])
                    difference() {
                        cylinder(h = body_t, d = eye_id + 2*eye_wall, center = true);
                        cylinder(h = body_t + 2, d = eye_id, center = true);
                    }
            // swivel housing block below the eye
            translate([-7, -body_t/2, -18]) cube([14, body_t, 12]);
        }
        // pivot pin bore (M3) — clip half rotates about this axis
        translate([0, 0, -12]) cylinder(h = 16, d = pivot_d, center = true);
    }
}

/* ---------- hook body with V-saddle ---------- */
module hook() {
    rotate([90, 0, 0]) linear_extrude(height = body_t, center = true) {
        // main C-hook: torus section minus mouth wedge
        difference() {
            circle(r = hook_r + wire_d);
            circle(r = hook_r);
            // mouth opening wedge (upper right)
            polygon([[0, 0],
                     [hook_r + wire_d + 5, mouth_gap * 0.55],
                     [hook_r + wire_d + 5, mouth_gap * 1.6]]);
        }
        // V-saddle at the bottom inside of the hook
        vy = -hook_r + 2;
        polygon([[-saddle_w/2, vy + saddle_w/2 * tan(90 - saddle_ang/2)],
                 [0, vy],
                 [ saddle_w/2, vy + saddle_w/2 * tan(90 - saddle_ang/2)],
                 [ saddle_w/2, vy - wire_d],
                 [-saddle_w/2, vy - wire_d]]);
    }
}

/* ---------- optional spring-gate stub ---------- */
module gate_stub() {
    // anchor boss for a printed-TPU flap or simple rubber band gate
    translate([hook_r * 0.72, 0, hook_r * 0.55])
        sphere(d = wire_d * 0.9);
}

/* ---------- assembly ---------- */
module clip() {
    translate([0, 0, hook_r + 30]) eye();
    translate([0, 0, hook_r + 12]) hook();
    if (gate) translate([0, 0, hook_r + 12]) gate_stub();
}

clip();

// Print notes:
//  * Orient with the hook plane flat on the bed; no supports needed except
//    under the eye — or split eye/hook at the pivot and bolt together (M3),
//    which also gives you the swivel for free.
//  * PETG, 4 perimeters, 40% infill is far beyond 1 kg strong.
