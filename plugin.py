#!/usr/bin/env python3
from time import sleep
import threading
import datetime
import sys
import os

# getcwd() isn't really accurate. So we have to do this weird stuff
cwd = sys.argv[0]
cwd = cwd[:cwd.rindex("/")]

package_dirname   = os.path.join(cwd, "packages")
package64_dirname = os.path.join(cwd, "packages64")

print(f"INIT: CWD is set to {cwd}")

if os.path.isdir(package_dirname):
    print("Package repository exists. Adding")
    sys.path.insert(0, package_dirname)

if os.path.isdir(package64_dirname):
    print("Package repository (for 64bit libraries) exists. Adding")
    sys.path.insert(0, package64_dirname)

import numpy as np
import pyaudio
import ffmpeg
import cv2

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gegl", "0.4")
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import GimpUi
from gi.repository import Gimp
from gi.repository import Gegl
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

class VideoPlayer(Gimp.PlugIn):
    def do_query_procedures(self):
        return [
            "plug-in-video-player"
        ]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(self, name,
                                            Gimp.PDBProcType.PLUGIN,
                                            self.run, None)

        procedure.set_image_types("*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)

        procedure.set_menu_label(_("Video Player"))
        procedure.set_icon_name(GimpUi.ICON_GEGL)
        procedure.add_menu_path("<Image>/Games")

        procedure.set_documentation(_("A GIMP Video Player"),
                                    _("A GIMP Video Player"),
                                    name)
        
        procedure.set_attribution("Greyson", "Greyson", "2024")

        return procedure

    def run(self, procedure, run_mode, image, n_drawables, drawables, config, run_data):        
        if n_drawables != 1:
            msg = _("Procedure '{}' only works with one drawable.").format(procedure.get_name())
            error = GLib.Error.new_literal(Gimp.PlugIn.error_quark(), msg, 0)
            return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, error)
        else:
            drawable = drawables[0]

        video_file = ""

        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init("gimp-videoplayer.py")

            dialog = GimpUi.Dialog(use_header_bar=True,
                                   title=_("Specify Video File"),
                                   role="gimp-video-file")

            dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
            dialog.add_button(_("_OK"), Gtk.ResponseType.OK)

            geometry = Gdk.Geometry()
            geometry.max_aspect = 0.2
            dialog.set_geometry_hints(None, geometry, Gdk.WindowHints.ASPECT)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            dialog.get_content_area().add(box)

            text_entry = Gtk.Entry()
            text_entry.set_text("")
            box.pack_start(text_entry, True, True, 0)

            box.show()

            while True:
                response = dialog.run()
                
                if response == Gtk.ResponseType.OK:
                    video_file = text_entry.get_text()
                    dialog.destroy()
                    break
                else:
                    dialog.destroy()
                    return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        intersect, x, y, width, height = drawable.mask_intersect()

        if video_file == "":
            video_file = os.path.join(cwd, "video.mp4")

        if intersect:
            Gegl.init(None)
            print(f"INFO: using video file '{video_file}'")

            procedure = Gimp.get_pdb().lookup_procedure("gimp-drawable-set-pixel")
            
            main_rect = Gegl.Rectangle.new(x, y, width, height)
            shadow_buffer = drawable.get_shadow_buffer()

            def draw_frame(pixels: np.ndarray) -> None:
                pixel_data = bytes(pixels[:,:,[2,1,0]].reshape(-1))

                shadow_buffer.set(main_rect, "RGB u8", pixel_data)
                shadow_buffer.flush()

                drawable.merge_shadow(True)
                drawable.update(x, y, width, height)
                Gimp.displays_flush()
            
            video = cv2.VideoCapture(video_file)

            fps = video.get(cv2.CAP_PROP_FPS)
            fps_in_ms = (1000/fps)/100

            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame = 1

            raw_audio_data, unknown = (ffmpeg
                    .input(video_file)
                    .output("-", format="s16le")
                    .overwrite_output()
                    .run(capture_stdout=True)
                    )
            
            out: list[bytes] = []

            # Magic way of calculating the size of the PCM recording for the size of each frame
            # https://stackoverflow.com/questions/17702439/calculate-size-of-1-minute-pcm-recording
            magic_calced_size_for_each_frame = int((44100 * (16 / 8) * 2) / (fps / 2))

            for current_position in range(0, len(raw_audio_data), magic_calced_size_for_each_frame):
                out.append(raw_audio_data[current_position:min(current_position+magic_calced_size_for_each_frame, len(raw_audio_data))])
            
            print("Done preprocessing audio.")

            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=2, rate=44100, output=True)
            
            def audio():
                print(f"INFO: the video frame count is {frame_count} and the audio frame count is {len(out)}")
                
                while int(current_frame / 2) < frame_count:
                    stream.write(out[int(current_frame / 2)])

                stream.stop_stream()
                stream.close()

            audio_thread = threading.Thread(target=audio)
            audio_thread.start()
            
            success, image = video.read()

            while success:
                sample_first = datetime.datetime.now()
                resized_image = cv2.resize(image, (width, height)) 
                draw_frame(resized_image)
                sample_second = datetime.datetime.now()

                delta = sample_second - sample_first
                ms = delta.total_seconds()*10

                frameskip_count = int(ms / fps_in_ms) + 1
                wait_time_until_next_frame = ms % fps_in_ms

                if frameskip_count > 1:
                    print(f"WARNING: Can't keep up! Skipping {frameskip_count-1} frame(s)")
                
                for i in range(frameskip_count):
                    success, image = video.read()

                current_frame += frameskip_count
                
                # Magic numbers for processing overhead
                sleep(wait_time_until_next_frame/10)

            print("INFO: Video stream has finished")

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

Gimp.main(VideoPlayer.__gtype__, sys.argv)
