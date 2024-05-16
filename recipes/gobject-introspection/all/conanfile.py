from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm, rmdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version
import os
import glob

required_conan_version = ">=1.53.0"

class GobjectIntrospectionConan(ConanFile):
    name = "gobject-introspection"
    description = "GObject introspection is a middleware layer between C libraries (using GObject) and language bindings"
    topics = ("gobject-instrospection")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gitlab.gnome.org/GNOME/gobject-introspection"
    license = "LGPL-2.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False], 
        "fPIC": [True, False]
    }
    default_options = {
        "shared": False, 
        "fPIC": True
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # for plain C projects only
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("dependency/0.8.1")

    def requirements(self):
        self.requires("glib/2.73.0")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder)

    def _configure_meson(self):
        meson = Meson(self)
        defs = dict()
        defs["build_introspection_data"] = self.options["glib"].shared
        defs["datadir"] = os.path.join(self.package_folder, "res")

        meson.configure(
            source_folder=self._source_subfolder,
            args=["--wrap-mode=nofallback"],
            build_folder=self._build_subfolder,
            defs=defs,
        )
        return meson

    def build(self):
        tools.replace_in_file(
            os.path.join(self._source_subfolder, "meson.build"),
            "subdir('tests')",
            "#subdir('tests')",
        )
        tools.replace_in_file(
            os.path.join(self._source_subfolder, "meson.build"),
            "if meson.version().version_compare('>=0.54.0')",
            "if false",
        )

        with tools.environment_append(
            VisualStudioBuildEnvironment(self).vars
            if self._is_msvc
            else {"PKG_CONFIG_PATH": self.build_folder}
        ):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        with tools.environment_append(
            VisualStudioBuildEnvironment(self).vars
        ) if self._is_msvc else tools.no_op():
            meson = self._configure_meson()
            meson.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "share"))
        for pdb_file in glob.glob(os.path.join(self.package_folder, "bin", "*.pdb")):
            os.unlink(pdb_file)

    def package_info(self):
        self.cpp_info.names["pkg_config"] = "gobject-introspection-1.0"
        self.cpp_info.libs = ["girepository-1.0"]
        self.cpp_info.includedirs.append(
            os.path.join("include", "gobject-introspection-1.0")
        )

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH env var with: {}".format(bin_path))
        self.env_info.PATH.append(bin_path)

        exe_ext = ".exe" if self.settings.os == "Windows" else ""

        pkgconfig_variables = {
            'datadir': '${prefix}/res',
            'bindir': '${prefix}/bin',
            'g_ir_scanner': '${bindir}/g-ir-scanner',
            'g_ir_compiler': '${bindir}/g-ir-compiler%s' % exe_ext,
            'g_ir_generate': '${bindir}/g-ir-generate%s' % exe_ext,
            'gidatadir': '${datadir}/gobject-introspection-1.0',
            'girdir': '${datadir}/gir-1.0',
            'typelibdir': '${libdir}/girepository-1.0',
        }
        self.cpp_info.set_property(
            "pkg_config_custom_content",
            "\n".join("%s=%s" % (key, value) for key,value in pkgconfig_variables.items()))
