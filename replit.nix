
{ pkgs }: {
  deps = [
    pkgs.python3Packages.pip
    pkgs.libGL
    pkgs.libGLU
    pkgs.xorg.libX11
    pkgs.xorg.libXrender
    pkgs.xorg.libXext
    pkgs.opencv
    pkgs.mesa
  ];
}
