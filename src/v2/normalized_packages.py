"""Abstraction for various response models used in V2 implementation."""

from collections import defaultdict
from typing import List, Tuple, Dict, Set
from src.v2.models import Package, Ecosystem
from f8a_utils.tree_generator import GolangDependencyTreeGenerator


class NormalizedPackages:
    """Duplicate free Package List."""

    def __init__(self, packages: List[Package], ecosystem: Ecosystem):
        """Create NormalizedPackages by removing all duplicates from packages."""
        self._packages = packages
        self._ecosystem = ecosystem
        self._dependency_graph: Dict[Package, Set[Package]] = defaultdict(set)
        for package in packages:
            # clone without dependencies field
            if ecosystem == "golang":
                package.name = package.name.split("@")[0]
                _, package.version = GolangDependencyTreeGenerator.clean_version(package.version)
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
