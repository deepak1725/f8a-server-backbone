"""Abstraction for various response models used in V2 implementation."""
import logging
from collections import defaultdict
from typing import List, Tuple, Dict, Set

from werkzeug.exceptions import BadRequest

from src.v2.models import Package, Ecosystem
from f8a_utils.tree_generator import GolangDependencyTreeGenerator
from f8a_utils.gh_utils import GithubUtils


logger = logging.getLogger(__name__)


class NormalizedPackages:
    """Duplicate free Package List."""

    def __init__(self, packages: List[Package], ecosystem: Ecosystem):
        """Create NormalizedPackages by removing all duplicates from packages."""
        self._packages = packages
        self._ecosystem = ecosystem
        self._dependency_graph: Dict[Package, Set[Package]] = defaultdict(set)
        for package in packages:
            # clone without dependencies field
            package_clone = Package(name=package.name, version=package.version)
            self._dependency_graph[package_clone] = self._dependency_graph[package_clone] or set()
            for trans_package in package.dependencies or []:
                trans_clone = Package(name=trans_package.name, version=trans_package.version)
                self._dependency_graph[package].add(trans_clone)
        # unfold set of Package into flat set of Package
        self._transtives: Set[Package] = {d for dep in self._dependency_graph.values() for d in dep}
        self._directs = frozenset(self._dependency_graph.keys())
        self._all = self._directs.union(self._transtives)

    @property
    def direct_dependencies(self) -> Tuple[Package]:
        """Immutable list of direct dependency Package."""
        return tuple(self._directs)

    @property
    def transitive_dependencies(self) -> Tuple[Package]:
        """Immutable list of transitives dependency Package."""
        return tuple(self._transtives)

    @property
    def all_dependencies(self) -> Tuple[Package]:
        """Union of all direct and transitives without duplicates."""
        return tuple(self._all)

    @property
    def dependency_graph(self) -> Dict[Package, Set[Package]]:
        """Return Package with it's transtive without duplicates."""
        return self._dependency_graph

    @property
    def ecosystem(self):
        """Ecosystem value."""
        return self._ecosystem


class GoNormalizedPackages(NormalizedPackages):
    """Duplicate free list of GoNormalised Packages."""

    def __init__(self, packages: List[Package], ecosystem: Ecosystem):
        """Create NormalizedPackages by removing all duplicates from packages."""
        self._packages = packages
        self._ecosystem = ecosystem
        self._dependency_graph: Dict[Package, Set[Package]] = defaultdict(set)
        self._modules = []
        self._version_map = {}
        gh = GithubUtils()
        self.pseudo = set()
        for package in packages:
            # clone without dependencies field
            package.name, package.version, \
                go_package_module = self.get_golang_metadata(package)
            package_clone = Package(name=package.name, version=package.version)
            if gh.is_pseudo_version(package.version):
                self._modules.append(go_package_module)
                self._version_map[package.name] = package.version
                self.pseudo.add(package_clone)
            self._dependency_graph[package_clone] = self._dependency_graph[package_clone] or set()
            for trans_package in package.dependencies or []:
                trans_package.name, trans_package.version, \
                    trans_module = self.get_golang_metadata(trans_package)
                trans_clone = Package(name=trans_package.name, version=trans_package.version)
                if gh.is_pseudo_version(trans_package.version):
                    self._modules.append(trans_module)
                    self._version_map[trans_package.name] = trans_package.version
                    self.pseudo.add(package_clone)
                self._dependency_graph[package].add(trans_clone)
        # unfold set of Package into flat set of Package
        self._transtives: Set[Package] = {d for dep in self._dependency_graph.values() for d in dep}
        self._directs = frozenset(self._dependency_graph.keys())
        self._all = self._directs.union(self._transtives)
        self._all_except_pseudo = self._all.difference(self.pseudo)

    @property
    def modules(self) -> Tuple[str]:
        """Get Tuple of Package Modules."""
        return tuple(set(self._modules))

    @property
    def version_map(self) -> Dict:
        """Map of Package_name: package_version."""
        return dict(self._version_map)

    @property
    def all_deps_without_pseudo(self) -> Tuple[Package]:
        """Diff of all direct deps and pseudo deps."""
        return tuple(self._all_except_pseudo)

    def get_golang_metadata(self, package) -> Tuple[str, str, str]:
        """Clean Package Name, Pkg version & get Golang package_module and version_map."""
        if "@" not in package.name:
            raise BadRequest("Package name should be of format package@module.")

        package_name, package_module = package.name.split("@")
        _, package_version = GolangDependencyTreeGenerator.clean_version(package.version)
        return package_name, package_version, package_module
