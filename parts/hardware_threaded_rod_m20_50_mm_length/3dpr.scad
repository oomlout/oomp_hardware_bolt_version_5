// Generated from working.yaml; units mm; length is end-to-end.
// Nominal metric fully threaded rod, cut to catalogue length
diameter = 20.0;
length = 50.0;
pitch = 2.5;
chamfer = pitch/2;
display = false;
segments = display ? 24 : 48;
steps = display ? 2 : ceil(length/pitch*16);
function depth(phase) = let(q=abs(phase-floor(phase+0.5)), h=sqrt(3)/2*pitch, r=h/6)
    q <= 3/8 ? max(0,(q-1/16)*pitch*sqrt(3)) :
    17*h/24-r+sqrt(max(0,r*r-pow((0.5-q)*pitch,2)));
epsilon = max(0.000001,length*0.0000002);
zs = concat([0],
    [for(i=[1:steps-1]) let(z=i*length/steps) if(z>epsilon && z<chamfer-epsilon) z],
    [chamfer],
    [for(i=[1:steps-1]) let(z=i*length/steps) if(z>chamfer+epsilon && z<length-chamfer-epsilon) z],
    [length-chamfer],
    [for(i=[1:steps-1]) let(z=i*length/steps) if(z>length-chamfer+epsilon && z<length-epsilon) z],
    [length]);
nr = len(zs);
points = concat([for (z=zs) for (j=[0:segments-1])
    let(a=j*360/segments, r=min(diameter/2-(display ? 0 : depth(z/pitch-j/segments)),diameter/2-chamfer+min(z,length-z)))
    [r*cos(a),r*sin(a),z]], [[0,0,0],[0,0,length]]);
// OpenSCAD polyhedron face winding is clockwise when viewed from outside.
faces = concat(
    [for(i=[0:nr-2]) for(j=[0:segments-1]) let(a=i*segments+j,b=i*segments+(j+1)%segments) [a,b+segments,b]],
    [for(i=[0:nr-2]) for(j=[0:segments-1]) let(a=i*segments+j,b=i*segments+(j+1)%segments) [a,a+segments,b+segments]],
    [for(j=[0:segments-1]) [nr*segments,j,(j+1)%segments]],
    [for(j=[0:segments-1]) [nr*segments+1,(nr-1)*segments+(j+1)%segments,(nr-1)*segments+j]]);
polyhedron(points,faces,convexity=10);
