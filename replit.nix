
{ pkgs }: {
  deps = [
    pkgs.libGLU
    pkgs.libGL
    pkgs.xorg.libX11
    pkgs.xorg.libXrender
    pkgs.xorg.libXext
    pkgs.opencv
    pkgs.python3Packages.dxf2svg
  ];
}
