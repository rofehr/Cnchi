#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ask.py
#
# Copyright © 2013-2016 Antergos
#
# This file is part of Cnchi.
#
# Cnchi is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Cnchi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# The following additional terms are in effect as per Section 7 of the license:
#
# The preservation of all legal notices and author attributions in
# the material or in the Appropriate Legal Notices displayed
# by works containing it is required.
#
# You should have received a copy of the GNU General Public License
# along with Cnchi; If not, see <http://www.gnu.org/licenses/>.


""" Asks which type of installation the user wants to perform """

import logging
import os
import subprocess
import time

import gi

import bootinfo

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ui.base import Page

import misc.extra as misc


def check_alongside_disk_layout():
    """ Alongside can only work if user has followed the recommended
        BIOS-Based Disk-Partition Configurations shown in
        http://technet.microsoft.com/en-us/library/dd744364(v=ws.10).aspx """

    # TODO: Add more scenarios where alongside could work

    partitions = misc.get_partitions()
    # logging.debug(partitions)
    extended = False
    for partition in partitions:
        if misc.is_partition_extended(partition):
            extended = True

    if extended:
        return False

    # We just seek for sda partitions
    partitions_sda = []
    for partition in partitions:
        if "sda" in partition:
            partitions_sda.append(partition)

    # There's no extended partition, so all partitions must be primary
    if len(partitions_sda) < 4:
        return True

    return False


def load_zfs():
    cmd = ["modprobe", "zfs"]
    try:
        with misc.raised_privileges():
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        logging.debug("ZFS kernel module loaded successfully.")
    except subprocess.CalledProcessError as err:
        logging.debug(
            "Can't load ZFS kernel module: %s",
            err.output.decode())
        return False
    return True


class InstallationAsk(Page):
    def __init__(self, params, prev_page="disk_group", next_page=None, **kwargs):
        super().__init__(self, params, name="installation_ask", prev_page=prev_page,
                         next_page=next_page, **kwargs)

        data_dir = self.settings.get("data")
        self.title = _('Install Mode')
        self.in_group = True

        partitioner_dir = os.path.join(
            data_dir,
            "images",
            "partitioner",
            "small")

        self.disable_rank_mirrors = params["disable_rank_mirrors"]

        self.ui_elements = {
            'automatic_image': '',
            'advanced_image': '',
            'automatic_radiobutton': '',
            'automatic_description': '',
            'encrypt_checkbutton': '',
            'encrypt_label': '',
            'lvm_checkbutton': '',
            'lvm_label': '',
            'zfs_checkbutton': '',
            'zfs_label': '',
            'home_checkbutton': '',
            'home_label': '',
            'introduction': '',
            'advanced_radiobutton': '',
            'advanced_description': ''
        }

        self.options_stack = self.ui.get_object('ask_stack_advanced')
        self.automatic_toggle_button = self.ui.get_object('automatic_radiobutton')
        self.advanced_toggle_button = self.ui.get_object('advanced_radiobutton')
        self.stack_wrapper = self.ui.get_object('stack_wrapper')

        self.stack_wrapper.show_all()
        automatic_options = self.ui.get_object('automatic_options_wrapper')
        advanced_options = self.ui.get_object('advanced_options_wrapper')
        self.options_stack.child_set_property(automatic_options, 'name', 'automatic_wrapper')
        self.options_stack.child_set_property(advanced_options, 'name', 'advanced_wrapper')
        self.show_all()
        self.options_stack.set_visible_child_name('advanced_wrapper')
        self.stack_wrapper.hide()

        self.other_oses = []

        # DISABLE ALONGSIDE INSTALLATION. IT'S NOT READY YET
        # enable_alongside = self.check_alongside()
        enable_alongside = False
        self.settings.set('enable_alongside', enable_alongside)
        '''
        if enable_alongside:
            msg = "Cnchi will enable the 'alongside' installation mode."
        else:
            msg = "Cnchi will NOT enable the 'alongside' installation mode."
        logging.debug(msg)
        '''
        # By default, select automatic installation
        self.next_page = "installation_automatic"
        self.settings.set("partition_mode", "automatic")

        self.is_zfs_available = load_zfs()

    def check_alongside(self):
        """ Check if alongside installation type must be enabled.
        Alongside only works when Windows is installed on sda  """

        enable_alongside = False

        # FIXME: Alongside does not work in UEFI systems
        if os.path.exists("/sys/firmware/efi"):
            msg = "The 'alongside' installation mode does not work in UEFI systems"
            logging.debug(msg)
            enable_alongside = False
        else:
            oses = bootinfo.get_os_dict()
            self.other_oses = []
            for key in oses:
                # We only check the first hard disk
                non_valid = ["unknown", "Swap", "Data or Swap", self.other_oses]
                if "sda" in key and oses[key] not in non_valid:
                    self.other_oses.append(oses[key])

            if self.other_oses:
                for detected_os in self.other_oses:
                    if "windows" in detected_os.lower():
                        logging.debug("Windows(tm) OS detected.")
                        enable_alongside = True
                if not enable_alongside:
                    logging.debug("Windows(tm) OS not detected.")
                    enable_alongside = False
            else:
                logging.debug("Can't detect any OS in device sda.")
                enable_alongside = False

            if not check_alongside_disk_layout():
                msg = "Unsuported disk layout for the 'alongside' installation mode"
                logging.debug(msg)
                enable_alongside = False

        return enable_alongside

    def enable_automatic_options(self, status):
        """ Enables or disables automatic installation options """
        names = [
            "encrypt_checkbutton",
            "encrypt_label",
            "lvm_checkbutton",
            "lvm_label",
            "home_checkbutton",
            "home_label"]

        for name in names:
            obj = self.ui.get_object(name)
            obj.set_sensitive(status)

        names = ["zfs_checkbutton", "zfs_label"]
        for name in names:
            obj = self.ui.get_object(name)
            obj.set_sensitive(status and self.is_zfs_available)

    def prepare(self, direction):
        """ Prepares screen """
        self.translate_ui()
        self.show_all()
        self.forward_button.set_sensitive(False)
        self.stack_wrapper.hide()

    def hide_option(self, option):
        """ Hides widgets """
        widgets = []
        if option == "alongside":
            widgets = [
                "alongside_radiobutton",
                "alongside_description",
                "alongside_image"]

        for name in widgets:
            widget = self.ui.get_object(name)
            if widget is not None:
                widget.hide()

    def get_os_list_str(self):
        """ Get string with the detected os names """
        os_str = ""
        len_other_oses = len(self.other_oses)
        if len_other_oses > 0:
            if len_other_oses > 1:
                if len_other_oses == 2:
                    os_str = _(" and ").join(self.other_oses)
                else:
                    os_str = ", ".join(self.other_oses)
            else:
                os_str = self.other_oses[0]

        # Truncate string if it's too large
        if len(os_str) > 40:
            os_str = os_str[:40] + "..."

        return os_str

    def translate_ui(self):
        """ Translates screen before showing it """

        oses_str = self.get_os_list_str()

        max_width_chars = 60


        # Alongside Install (For now, only works with Windows)
        # if len(oses_str) > 0:
        #     txt = _("Install Antergos alongside {0}").format(oses_str)
        #     radio = self.ui.get_object("alongside_radiobutton")
        #     radio.set_label(txt)
        #
        #     label = self.ui.get_object("alongside_description")
        #     txt = _("Installs Antergos without removing {0}").format(oses_str)
        #     txt = description_style.format(txt)
        #     label.set_markup(txt)
        #     label.set_line_wrap(True)
        #
        #     intro_txt = _("This computer has {0} installed.").format(oses_str)
        #     intro_txt = intro_txt + "\n" + _("What do you want to do?")
        # else:

        # Advanced Install
        # radio = self.ui.get_object("advanced_radiobutton")
        # for child in radio.get_children():
        #     if isinstance(child, Gtk.Label):
        #         child.set_max_width_chars(50)
        #         child.set_line_wrap(True)

    def store_values(self):
        """ Store selected values """
        check = self.ui.get_object("encrypt_checkbutton")
        use_luks = check.get_active()

        check = self.ui.get_object("lvm_checkbutton")
        use_lvm = check.get_active()

        check = self.ui.get_object("zfs_checkbutton")
        use_zfs = check.get_active()

        check = self.ui.get_object("home_checkbutton")
        use_home = check.get_active()

        if self.next_page == "installation_automatic":
            self.settings.set('use_lvm', use_lvm)
            self.settings.set('use_luks', use_luks)
            self.settings.set('use_luks_in_root', True)
            self.settings.set('luks_root_volume', "cryptAntergos")
            self.settings.set('use_zfs', False)
            self.settings.set('use_home', use_home)
        elif self.next_page == "installation_zfs":
            self.settings.set('use_lvm', False)
            self.settings.set('use_luks', use_luks)
            self.settings.set('use_luks_in_root', False)
            self.settings.set('luks_root_volume', "")
            self.settings.set('use_zfs', True)
            self.settings.set('zfs', True)
            self.settings.set('use_home', use_home)
        else:
            # Set defaults. We don't know these yet.
            self.settings.set('use_lvm', False)
            self.settings.set('use_luks', False)
            self.settings.set('use_luks_in_root', False)
            self.settings.set('luks_root_volume', "")
            self.settings.set('use_zfs', False)
            self.settings.set('use_home', False)

        if not self.settings.get('use_zfs'):
            if self.settings.get('use_luks'):
                logging.info("Antergos installation will be encrypted using LUKS")
            if self.settings.get('use_lvm'):
                logging.info("Antergos will be installed using LVM volumes")
                if self.settings.get('use_home'):
                    logging.info("Antergos will be installed using a separate /home volume.")
            elif self.settings.get('use_home'):
                logging.info("Antergos will be installed using a separate /home partition.")
        else:
            logging.info("Antergos will be installed using ZFS")
            if self.settings.get('use_luks'):
                logging.info("Antergos ZFS installation will be encrypted")
            if self.settings.get('use_home'):
                logging.info("Antergos will be installed using a separate /home volume.")

        if self.next_page == "installation_alongside":
            self.settings.set('partition_mode', 'alongside')
        elif self.next_page == "installation_advanced":
            self.settings.set('partition_mode', 'advanced')
        elif self.next_page == "installation_automatic":
            self.settings.set('partition_mode', 'automatic')
        elif self.next_page == "installation_zfs":
            self.settings.set('partition_mode', 'zfs')

        # Check if there are still processes running...
        self.wait()

        return True

    def wait(self):
        """ Check if there are still processes running and
            waits for them to finish """
        must_wait = False
        for proc in self.process_list:
            if proc.is_alive():
                must_wait = True
                break

        if not must_wait or self.disable_rank_mirrors:
            return

        txt1 = _("Ranking mirrors")
        txt1 = "<big>{0}</big>".format(txt1)

        txt2 = _("Cnchi is still updating and optimizing your mirror lists.")
        txt2 += "\n\n"
        txt2 += _("Please be patient...")
        txt2 = "<i>{0}</i>".format(txt2)

        wait_ui = Gtk.Builder()
        ui_file = os.path.join(self.ui_dir, "wait.ui")
        wait_ui.add_from_file(ui_file)

        lbl1 = wait_ui.get_object("label1")
        lbl1.set_markup(txt1)

        lbl2 = wait_ui.get_object("label2")
        lbl2.set_markup(txt2)

        progress_bar = wait_ui.get_object("progressbar")

        wait_window = wait_ui.get_object("wait_window")
        wait_window.set_modal(True)
        wait_window.set_transient_for(self.get_main_window())
        wait_window.set_default_size(320, 240)
        wait_window.set_position(Gtk.WindowPosition.CENTER)
        wait_window.show_all()

        ask_box = self.ui.get_object("ask")
        if ask_box:
            ask_box.set_sensitive(False)

        logging.debug("Waiting for all external processes to finish...")
        while must_wait:
            must_wait = False
            for proc in self.process_list:
                # This waits until process finishes, no matter the time.
                if proc.is_alive():
                    must_wait = True
            # Just wait...
            time.sleep(0.1)
            # Update our progressbar dialog
            progress_bar.pulse()
            while Gtk.events_pending():
                Gtk.main_iteration()
        logging.debug(
            "All external processes are finished. Installation can go on")
        wait_window.hide()

        if ask_box:
            ask_box.set_sensitive(True)

    def get_next_page(self):
        return self.next_page

    def on_automatic_radiobutton_toggled(self, widget):
        """ Automatic selected, enable all options """
        if widget.get_active():
            self.enable_automatic_options(True)
            self.stack_wrapper.show_all()
            self.options_stack.set_visible_child_name('automatic_wrapper')
            self.forward_button.set_sensitive(True)

            if self.advanced_toggle_button.get_active():
                self.advanced_toggle_button.set_active(False)

            check = self.ui.get_object("zfs_checkbutton")
            if check.get_active():
                self.next_page = "installation_zfs"
            else:
                self.next_page = "installation_automatic"

    def on_automatic_lvm_checkbutton_toggled(self, widget):
        if widget.get_active():
            self.next_page = "installation_automatic"
            check = self.ui.get_object("zfs_checkbutton")
            if check.get_active():
                check.set_active(False)

    def on_automatic_zfs_checkbutton_toggled(self, widget):
        if widget.get_active():
            self.next_page = "installation_zfs"
            check = self.ui.get_object("lvm_checkbutton")
            if check.get_active():
                check.set_active(False)
        else:
            self.next_page = "installation_automatic"

    def on_alongside_radiobutton_toggled(self, widget):
        """ Alongside selected, disable all automatic options """
        if widget.get_active():
            self.next_page = "installation_alongside"
            self.enable_automatic_options(False)

    def on_advanced_radiobutton_toggled(self, widget):
        """ Advanced selected, disable all automatic options """
        if widget.get_active():
            self.next_page = "installation_advanced"
            self.enable_automatic_options(False)
            self.forward_button.set_sensitive(True)
            self.options_stack.set_visible_child_name('advanced_wrapper')
            self.stack_wrapper.hide()

            if self.automatic_toggle_button.get_active():
                self.automatic_toggle_button.set_active(False)


if __name__ == '__main__':
    from test_screen import _, run

    run('InstallationAsk')
