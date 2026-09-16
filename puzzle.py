"""
Queens Gambit - Puzzle Generation Engine

Generates NxN grids with N colored regions. Each puzzle requires placing
2 queens per region, 2 per row, and 2 per column, with no two queens
adjacent (including diagonals — king-distance constraint).

This is equivalent to the "Star Battle 2" puzzle type.
"""

import random
import time
from collections import deque
from itertools import combinations


class Puzzle:
    """Represents a Queens Gambit puzzle."""

    def __init__(self, n, grid, solution):
        """
        Args:
            n: Grid size (NxN).
            grid: 2D list where grid[r][c] = color index (0 to n-1).
            solution: Set of (row, col) tuples — the valid queen positions.
        """
        self.n = n
        self.grid = grid
        self.solution = frozenset(solution)

    def check_placement(self, row, col):
        """Check if placing a queen at (row, col) is part of the solution."""
        return (row, col) in self.solution

    def get_color(self, row, col):
        """Get the color index of a cell."""
        return self.grid[row][col]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_sample_puzzle():
    """
    Return a hardcoded, verified-valid 9×9 puzzle for immediate use.
    Avoids the need for runtime generation.
    """
    grid = [
        [3, 3, 3, 6, 6, 6, 8, 8, 8],
        [8, 3, 6, 6, 6, 6, 8, 8, 8],
        [8, 3, 3, 6, 8, 8, 8, 7, 7],
        [8, 3, 1, 1, 8, 4, 4, 7, 7],
        [8, 1, 1, 1, 8, 4, 4, 7, 7],
        [8, 1, 1, 8, 8, 4, 4, 5, 7],
        [8, 8, 8, 8, 0, 5, 5, 5, 5],
        [2, 2, 2, 0, 0, 0, 5, 5, 5],
        [2, 2, 2, 2, 0, 0, 0, 5, 5],
    ]
    solution = {
        (0, 2), (0, 7),
        (1, 0), (1, 5),
        (2, 3), (2, 7),
        (3, 1), (3, 5),
        (4, 3), (4, 8),
        (5, 1), (5, 6),
        (6, 4), (6, 8),
        (7, 2), (7, 6),
        (8, 0), (8, 4),
    }
    return Puzzle(9, grid, solution)


def generate_puzzle(n=10, max_time=30):
    """
    Generate a complete puzzle: queen positions + colored regions.

    Args:
        n: Grid size (minimum 8 for the 2-queen variant).
        max_time: Maximum seconds to spend generating before giving up.

    Returns:
        Puzzle object, or None if generation failed.
    """
    deadline = time.time() + max_time

    while time.time() < deadline:
        queens = _generate_queens(n, deadline)
        if queens is None:
            continue

        # Try several pairings with smart matching
        for _ in range(30):
            if time.time() >= deadline:
                return None

            pairs = _smart_pair(list(queens), n)
            grid = _grow_regions_bridged(pairs, n)
            if grid is not None:
                return Puzzle(n, grid, queens)

    return None


# ---------------------------------------------------------------------------
# Queen Placement (Backtracking)
# ---------------------------------------------------------------------------

def _generate_queens(n, deadline=None):
    """
    Place 2 queens per row on an NxN grid so that:
    - Each column has exactly 2 queens.
    - No two queens are king-distance adjacent (including diagonals).

    Returns a set of (row, col) tuples, or None.
    """
    col_counts = [0] * n
    rows = []  # Each entry: (col1, col2) for that row

    def backtrack(row):
        if deadline and time.time() >= deadline:
            return False

        if row == n:
            return all(c == 2 for c in col_counts)

        remaining = n - row

        # Feasibility: can the remaining rows satisfy column requirements?
        slots_available = sum(
            min(2 - col_counts[c], remaining) for c in range(n)
        )
        if slots_available < remaining * 2:
            return False

        # Columns still accepting queens
        available = [c for c in range(n) if col_counts[c] < 2]
        if len(available) < 2:
            return False

        combos = list(combinations(available, 2))
        random.shuffle(combos)

        for c1, c2 in combos:
            # Queens in the same row must be at least 2 apart
            if abs(c1 - c2) <= 1:
                continue

            # Check king-distance with previous row's queens
            if row > 0:
                pc1, pc2 = rows[row - 1]
                conflict = False
                for c in (c1, c2):
                    for pc in (pc1, pc2):
                        if abs(c - pc) <= 1:
                            conflict = True
                            break
                    if conflict:
                        break
                if conflict:
                    continue

            # Place queens and recurse
            col_counts[c1] += 1
            col_counts[c2] += 1
            rows.append((c1, c2))

            if backtrack(row + 1):
                return True

            rows.pop()
            col_counts[c1] -= 1
            col_counts[c2] -= 1

        return False

    if backtrack(0):
        queens = set()
        for r, (c1, c2) in enumerate(rows):
            queens.add((r, c1))
            queens.add((r, c2))
        return queens

    return None


# ---------------------------------------------------------------------------
# Smart Queen Pairing
# ---------------------------------------------------------------------------

def _smart_pair(queen_list, n):
    """
    Pair 2N queens into N pairs, preferring pairs whose queens are
    close together (Manhattan distance) so region contiguity is easier.

    Uses a randomised greedy approach: randomly choose a queen, then pair
    it with its nearest unmatched queen.
    """
    remaining = list(queen_list)
    random.shuffle(remaining)
    pairs = []

    while remaining:
        q1 = remaining.pop(0)

        # Find closest unmatched queen (Manhattan distance)
        best_idx = 0
        best_dist = float("inf")
        for i, q2 in enumerate(remaining):
            d = abs(q1[0] - q2[0]) + abs(q1[1] - q2[1])
            # Add randomness so we don't always get the same pairing
            d += random.random() * 3
            if d < best_dist:
                best_dist = d
                best_idx = i

        q2 = remaining.pop(best_idx)
        pairs.append((q1, q2))

    return pairs


# ---------------------------------------------------------------------------
# Region Generation (Bridge-First BFS)
# ---------------------------------------------------------------------------

def _grow_regions_bridged(pairs, n):
    """
    Grow N contiguous colored regions from queen-pair seeds.

    Phase 1: For each pair, BFS-connect the two queens to ensure
             each region is contiguous from the start.
    Phase 2: Round-robin BFS to fill remaining cells.
    Phase 3: Verify contiguity.

    Returns NxN grid of color indices, or None on failure.
    """
    grid = [[-1] * n for _ in range(n)]
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # Seed each pair
    for color, (q1, q2) in enumerate(pairs):
        grid[q1[0]][q1[1]] = color
        grid[q2[0]][q2[1]] = color

    # Phase 1: Bridge each pair with a BFS path
    for color, (q1, q2) in enumerate(pairs):
        if not _bridge_queens(grid, q1, q2, color, n, DIRS):
            return None  # Couldn't bridge — try a different pairing

    # Phase 2: Round-robin BFS fill
    frontiers = _build_frontiers(grid, n, DIRS)
    unassigned = sum(1 for r in range(n) for c in range(n) if grid[r][c] == -1)

    max_iters = n * n * 2  # Safety limit
    iters = 0
    while unassigned > 0 and iters < max_iters:
        iters += 1
        progress = False
        order = list(range(n))
        random.shuffle(order)

        for color in order:
            # Attempt one expansion
            attempts = len(frontiers[color])
            for _ in range(attempts):
                if not frontiers[color]:
                    break
                r, c = frontiers[color].popleft()
                if grid[r][c] == -1:
                    grid[r][c] = color
                    unassigned -= 1
                    progress = True
                    for dr, dc in DIRS:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == -1:
                            frontiers[color].append((nr, nc))
                    break

        if not progress:
            # Assign orphans to any adjacent colour
            found = False
            for r in range(n):
                for c in range(n):
                    if grid[r][c] == -1:
                        for dr, dc in DIRS:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] != -1:
                                grid[r][c] = grid[nr][nc]
                                unassigned -= 1
                                frontiers[grid[r][c]].append((r, c))
                                found = True
                                break
                    if found:
                        break
                if found:
                    break
            if not found:
                return None

    # Phase 3: Verify contiguity
    if not _all_regions_contiguous(grid, n, DIRS):
        return None

    return grid


def _bridge_queens(grid, q1, q2, color, n, dirs):
    """
    BFS from q1 to q2, carving a path through unassigned cells.
    Assigns all path cells to *color*.  Returns True on success.
    """
    # If already adjacent/connected, nothing to do
    if q1 == q2:
        return True

    # BFS from q1, only through unassigned cells or cells of this color
    parent = {q1: None}
    queue = deque([q1])

    while queue:
        r, c = queue.popleft()
        if (r, c) == q2:
            # Trace back and assign colour
            cur = q2
            while cur is not None:
                grid[cur[0]][cur[1]] = color
                cur = parent[cur]
            return True
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and (nr, nc) not in parent:
                cell_val = grid[nr][nc]
                if cell_val == -1 or cell_val == color or (nr, nc) == q2:
                    parent[(nr, nc)] = (r, c)
                    queue.append((nr, nc))

    return False  # No path found


def _build_frontiers(grid, n, dirs):
    """Build BFS frontier lists for every colour from current grid state."""
    frontiers = [deque() for _ in range(n)]
    for r in range(n):
        for c in range(n):
            col = grid[r][c]
            if col == -1:
                continue
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == -1:
                    frontiers[col].append((nr, nc))
    # Deduplicate (order preserved)
    for i in range(n):
        seen = set()
        unique = deque()
        for cell in frontiers[i]:
            if cell not in seen:
                seen.add(cell)
                unique.append(cell)
        frontiers[i] = unique
    return frontiers


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _all_regions_contiguous(grid, n, dirs=None):
    """Verify every colour region is a single connected component."""
    if dirs is None:
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for color in range(n):
        cells = set()
        start = None
        for r in range(n):
            for c in range(n):
                if grid[r][c] == color:
                    cells.add((r, c))
                    if start is None:
                        start = (r, c)

        if not cells or len(cells) < 2:
            return False

        # BFS connectivity check
        visited = {start}
        queue = deque([start])
        while queue:
            r, c = queue.popleft()
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if (nr, nc) in cells and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

        if visited != cells:
            return False

    return True


def validate_editor_grid(grid, n):
    """
    Validate a user-painted editor grid before attempting to solve it.

    Args:
        grid: NxN 2-D list; cell value is color index (0..n-1) or -1 (unset).
        n: Expected grid size.

    Returns:
        (is_valid: bool, error_message: str)
    """
    from collections import Counter

    # All cells must be painted
    for r in range(n):
        for c in range(n):
            if grid[r][c] == -1:
                return False, f"All {n}\u00d7{n} cells must be painted"

    color_counts = Counter(grid[r][c] for r in range(n) for c in range(n))

    # Exactly n distinct colors, labeled 0 .. n-1
    if set(color_counts.keys()) != set(range(n)):
        missing = sorted(set(range(n)) - set(color_counts.keys()))
        return False, f"Colors {[m + 1 for m in missing]} have no cells \u2014 use all {n} colors"

    # Every region must be contiguous
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if not _all_regions_contiguous(grid, n, DIRS):
        return False, "Each color region must be one connected shape (no isolated islands)"

    # Every region needs at least 2 cells (two queens per region)
    for ci in range(n):
        if color_counts[ci] < 2:
            return False, f"Color region {ci + 1} needs at least 2 cells (it has {color_counts[ci]})"

    return True, ""


def solve_puzzle(grid, n):
    """
    Given a user-painted NxN grid with exactly n color regions (0..n-1),
    find a valid queen placement using Star Battle 2 rules:
      - 2 queens per row, column, and color region
      - No two queens king-distance adjacent

    Args:
        grid: Validated NxN 2-D list of color indices.
        n:    Grid / region count.

    Returns:
        Puzzle object on success, or None if no solution exists.
    """
    col_counts = [0] * n
    color_counts = [0] * n
    rows = []  # each entry: (c1, c2) placed in that row

    def backtrack(row):
        if row == n:
            return (all(c == 2 for c in col_counts) and
                    all(c == 2 for c in color_counts))

        remaining = n - row

        # Feasibility: available column slots
        slots = sum(min(2 - col_counts[c], remaining) for c in range(n))
        if slots < remaining * 2:
            return False

        for c1 in range(n):
            if col_counts[c1] >= 2:
                continue
            for c2 in range(c1 + 1, n):
                if col_counts[c2] >= 2:
                    continue
                # Queens in same row must be at least 2 apart
                if abs(c1 - c2) <= 1:
                    continue

                # King-distance adjacency with previous row
                if rows:
                    pc1, pc2 = rows[-1]
                    if (abs(c1 - pc1) <= 1 or abs(c1 - pc2) <= 1 or
                            abs(c2 - pc1) <= 1 or abs(c2 - pc2) <= 1):
                        continue

                ci1 = grid[row][c1]
                ci2 = grid[row][c2]

                # Color region constraints
                if color_counts[ci1] >= 2:
                    continue
                if ci1 == ci2 and color_counts[ci1] >= 1:
                    continue
                if ci2 != ci1 and color_counts[ci2] >= 2:
                    continue

                # Place
                col_counts[c1] += 1
                col_counts[c2] += 1
                color_counts[ci1] += 1
                color_counts[ci2] += 1
                rows.append((c1, c2))

                if backtrack(row + 1):
                    return True

                rows.pop()
                col_counts[c1] -= 1
                col_counts[c2] -= 1
                color_counts[ci1] -= 1
                color_counts[ci2] -= 1

        return False

    if backtrack(0):
        queens = set()
        for r, (c1, c2) in enumerate(rows):
            queens.add((r, c1))
            queens.add((r, c2))
        return Puzzle(n, [row[:] for row in grid], queens)

    return None


def verify_solution(placed_queens, puzzle):
    """
    Verify whether a set of queen positions is a valid solution.

    Args:
        placed_queens: Set of (row, col) tuples.
        puzzle: Puzzle object.

    Returns:
        (is_valid, list_of_error_strings)
    """
    n = puzzle.n
    errors = []

    if len(placed_queens) != 2 * n:
        errors.append(f"Need {2 * n} queens, have {len(placed_queens)}")

    # Row counts
    for r in range(n):
        cnt = sum(1 for row, _ in placed_queens if row == r)
        if cnt != 2:
            errors.append(f"Row {r}: {cnt} queens (need 2)")

    # Column counts
    for c in range(n):
        cnt = sum(1 for _, col in placed_queens if col == c)
        if cnt != 2:
            errors.append(f"Col {c}: {cnt} queens (need 2)")

    # Colour counts
    for color in range(n):
        cnt = sum(
            1 for r, c in placed_queens if puzzle.grid[r][c] == color
        )
        if cnt != 2:
            errors.append(f"Color {color}: {cnt} queens (need 2)")

    # King-distance adjacency
    ql = list(placed_queens)
    for i in range(len(ql)):
        for j in range(i + 1, len(ql)):
            r1, c1 = ql[i]
            r2, c2 = ql[j]
            if abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                errors.append(
                    f"Adjacent queens at ({r1},{c1}) and ({r2},{c2})"
                )

    return len(errors) == 0, errors
