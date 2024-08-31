# Welcome to Hell.
#
# We need to include nixpkgs in twice because if we don't, it compiles every package from source.
# Don't fix this (unless gimp 3.99/4.0 is upstreamed, in which case remove this awful hack)

{}: let
  pkgsUnstableTarball = fetchTarball https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz;
  
  pkgs = import pkgsUnstableTarball {
    overlays = [
      (final: prev: {
        gegl = prev.gegl.overrideAttrs (oldAttrs: {
          src = prev.fetchgit {
            url = "https://gitlab.gnome.org/GNOME/gegl.git";
            rev = "237b8cbb20d098aaab1f7533e1aed8c194c50ad9";
            sha256 = "yTvzkrM2ft+0Hr9Gl4Cjnjp6dU4BY+7r8Uc6Qf+SUuk=";
          };

          version = "0.4.49";
          doCheck = false;
        });
      })
    ];
  };

  gimp299UnstableGit  = fetchGit {
    url = "https://github.com/jtojnar/nixpkgs";
    rev = "1e5a160acf3990c33347a0517f12ad8596bd7cfe";
    ref = "gimp-meson";
  };

  gimp299Unstable = import gimp299UnstableGit {
    overlays = [
      (final: prev: {
        gimp = prev.gimp.overrideAttrs (oldAttrs: {
          # Mo speed mo betta
          buildInputs = [
            pkgs.appstream-glib # for library
            pkgs.babl
            pkgs.cfitsio
            pkgs.gegl
            pkgs.gtk3
            pkgs.glib
            pkgs.gdk-pixbuf
            pkgs.pango
            pkgs.cairo
            pkgs.libarchive
            pkgs.gexiv2
            pkgs.harfbuzz
            pkgs.isocodes
            pkgs.freetype
            pkgs.fontconfig
            pkgs.lcms
            pkgs.libpng
            pkgs.libjpeg
            pkgs.libjxl
            pkgs.poppler
            pkgs.poppler_data
            pkgs.libtiff
            pkgs.openexr
            pkgs.libmng
            pkgs.librsvg
            pkgs.libwmf
            pkgs.zlib
            pkgs.libzip
            pkgs.ghostscript
            pkgs.aalib
            pkgs.shared-mime-info
            pkgs.json-glib
            pkgs.libwebp
            pkgs.libheif
            pkgs.python3
            pkgs.libexif
            pkgs.xorg.libXpm
            pkgs.xorg.libXmu
            pkgs.glib-networking
            pkgs.libmypaint
            pkgs.mypaint-brushes1

            pkgs.python312Packages.pygobject3

            # New file dialogue crashes with “Icon 'image-missing' not present in theme Symbolic” without an icon theme.
            pkgs.adwaita-icon-theme

            # for Lua plug-ins
            (pkgs.luajit.withPackages (pp: [
              pp.lgi
            ]))
          ] ++ pkgs.lib.optionals (!pkgs.stdenv.isDarwin) [
            pkgs.alsa-lib

            # for JavaScript plug-ins
            pkgs.gjs
          ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            pkgs.AppKit
            pkgs.Cocoa
            pkgs.gtk-mac-integration-gtk3
          ] ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            pkgs.libgudev
          ];

          # needed by gimp-2.0.pc
          propagatedBuildInputs = [
            pkgs.gegl
          ];
        });
      })
    ];
  };
in pkgs.mkShell {
  stdenv = pkgs.clangStdenv;

  buildInputs = with pkgs; [ 
    gimp299Unstable.gimp
    python310
    python310Packages.pip
    python310Packages.setuptools
  ];
}