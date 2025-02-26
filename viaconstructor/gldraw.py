"""OpenGL drawing functions"""

import math
from typing import Sequence

import ezdxf
from OpenGL import GL
from OpenGL.GLU import (
    GLU_TESS_BEGIN,
    GLU_TESS_COMBINE,
    GLU_TESS_END,
    GLU_TESS_VERTEX,
    GLU_TESS_WINDING_ODD,
    GLU_TESS_WINDING_RULE,
    gluDeleteTess,
    gluNewTess,
    gluTessBeginContour,
    gluTessBeginPolygon,
    gluTessCallback,
    gluTessEndContour,
    gluTessEndPolygon,
    gluTessProperty,
    gluTessVertex,
)

from .calc import angle_of_line, calc_distance, line_center_3d
from .ext.HersheyFonts.HersheyFonts import HersheyFonts
from .preview_plugins.gcode import GcodeParser
from .preview_plugins.hpgl import HpglParser

font = HersheyFonts()
font.load_default_font()
font.normalize_rendering(6)


def draw_circle(center: Sequence[float], radius: float) -> None:
    """draws an circle"""
    GL.glBegin(GL.GL_TRIANGLE_STRIP)
    GL.glVertex3f(center[0], center[1], center[2])
    angle = 0.0
    step = math.pi / 6
    while angle < math.pi * 2 + step:
        p_x = center[0] + radius * math.sin(angle)
        p_y = center[1] - radius * math.cos(angle)
        GL.glVertex3f(p_x, p_y, center[2])
        GL.glVertex3f(center[0], center[1], center[2])
        angle += step
    GL.glEnd()


def draw_mill_line(
    p_from: Sequence[float],
    p_to: Sequence[float],
    width: float,
    mode: str,
    options: str,
) -> None:
    """draws an milling line including direction and width"""
    line_angle = angle_of_line(p_from, p_to)
    radius = width / 2

    if p_from[2] < 0.0 and p_to[2] < 0.0 and mode == "full":
        GL.glColor3f(1.0, 1.0, 0.0)
        # start/end circles
        draw_circle(p_from, radius)
        draw_circle(p_to, radius)
        x_out_from = p_from[0] + radius * math.sin(line_angle)
        y_out_from = p_from[1] - radius * math.cos(line_angle)
        x_in_from = p_from[0] + radius * math.sin(line_angle + math.pi)
        y_in_from = p_from[1] - radius * math.cos(line_angle + math.pi)
        x_out_to = p_to[0] + radius * math.sin(line_angle)
        y_out_to = p_to[1] - radius * math.cos(line_angle)
        x_in_to = p_to[0] + radius * math.sin(line_angle + math.pi)
        y_in_to = p_to[1] - radius * math.cos(line_angle + math.pi)

        # filled line
        GL.glBegin(GL.GL_TRIANGLE_STRIP)
        GL.glVertex3f(x_in_from, y_in_from, p_from[2])
        GL.glVertex3f(x_out_from, y_out_from, p_from[2])
        GL.glVertex3f(x_in_to, y_in_to, p_to[2])
        GL.glVertex3f(x_out_to, y_out_to, p_to[2])
        GL.glEnd()

    # center line
    if options != "OFF":
        GL.glColor3f(0.91, 0.0, 0.0)
    else:
        GL.glColor3f(0.11, 0.63, 0.36)
    GL.glBegin(GL.GL_LINES)
    GL.glVertex3fv(p_from)
    GL.glVertex3fv(p_to)
    GL.glEnd()

    if mode != "minimal":
        lenght = calc_distance(p_from, p_to)
        if lenght < 3:
            return
        # direction arrow
        GL.glColor3f(0.62, 0.73, 0.82)
        center = p_from
        if lenght > 5.0:
            center = line_center_3d(p_from, p_to)
        x_arrow = center[0] - 3 * math.sin(line_angle + math.pi / 2.0)
        y_arrow = center[1] + 3 * math.cos(line_angle + math.pi / 2.0)
        x_arrow_left = x_arrow + 1 * math.sin(line_angle + math.pi)
        y_arrow_left = y_arrow - 1 * math.cos(line_angle + math.pi)
        x_arrow_right = x_arrow + 1 * math.sin(line_angle)
        y_arrow_right = y_arrow - 1 * math.cos(line_angle)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(center[0], center[1], center[2] + 0.01)
        GL.glVertex3f(x_arrow_left, y_arrow_left, center[2] + 0.01)
        GL.glVertex3f(center[0], center[1], center[2] + 0.01)
        GL.glVertex3f(x_arrow_right, y_arrow_right, center[2] + 0.01)
        GL.glEnd()


def draw_text(
    text: str,
    pos_x: float,
    pos_y: float,
    pos_z: float,
    scale: float = 1.0,
    center_x: bool = False,
    center_y: bool = False,
) -> None:
    test_data = tuple(font.lines_for_text(text))
    if center_x or center_y:
        width = 0.0
        height = 0.0
        for (x_1, y_1), (x_2, y_2) in test_data:
            width = max(width, x_1 * scale)
            width = max(width, x_2 * scale)
            height = max(height, y_1 * scale)
            height = max(height, y_2 * scale)
        if center_x:
            pos_x -= width / 2.0
        if center_y:
            pos_y -= height / 2.0
    for (x_1, y_1), (x_2, y_2) in test_data:
        GL.glVertex3f(pos_x + x_1 * scale, pos_y + y_1 * scale, pos_z)
        GL.glVertex3f(pos_x + x_2 * scale, pos_y + y_2 * scale, pos_z)


def draw_grid(project: dict) -> None:
    """draws the grid"""
    min_max = project["minMax"]
    size = project["setup"]["view"]["grid_size"]
    start_x = int(min_max[0] / size) * size - size
    end_x = int(min_max[2] / size) * size + size
    start_y = int(min_max[1] / size) * size - size
    end_y = int(min_max[3] / size) * size + size
    size_x = min_max[2] - min_max[0]
    center_x = min_max[0] + size_x / 2
    size_y = min_max[3] - min_max[1]
    center_y = min_max[1] + size_y / 2
    z_offset = -project["setup"]["workpiece"]["offset_z"]
    mill_depth = project["setup"]["mill"]["depth"]
    unit = project["setup"]["machine"]["unit"]
    unitscale = 1.0
    if unit == "inch":
        unitscale = 25.4
        z_offset *= unitscale
        mill_depth *= unitscale

    if project["setup"]["view"]["grid_show"]:
        # Grid-X
        GL.glLineWidth(0.1)
        GL.glColor3f(0.9, 0.9, 0.9)
        GL.glBegin(GL.GL_LINES)
        for p_x in range(start_x, end_x + size, size):
            GL.glVertex3f(p_x, start_y, mill_depth)
            GL.glVertex3f(p_x, end_y, mill_depth)
        if project["setup"]["view"]["ruler_show"] and size >= 5:
            for p_x in range(start_x, end_x, size):
                draw_text(f"{p_x}", p_x, start_y, mill_depth, 0.4)
        GL.glEnd()

        # Grid-Y
        GL.glLineWidth(0.1)
        GL.glColor3f(0.9, 0.9, 0.9)
        GL.glBegin(GL.GL_LINES)
        for p_y in range(start_y, end_y + size, size):
            GL.glVertex3f(start_x, p_y, mill_depth)
            GL.glVertex3f(end_x, p_y, mill_depth)
        if project["setup"]["view"]["ruler_show"] and size >= 5:
            for p_y in range(start_y, end_y, size):
                draw_text(f"{p_y}", start_x, p_y, mill_depth, 0.4)
        GL.glEnd()

    # Zero-Z
    GL.glLineWidth(1)
    GL.glColor3f(1.0, 1.0, 0.0)
    GL.glBegin(GL.GL_LINES)
    GL.glVertex3f(0.0, 0.0, 100.0)
    GL.glVertex3f(0.0, 0.0, mill_depth)
    GL.glVertex3f(-1, -1, 0.0)
    GL.glVertex3f(1, 1, 0.0)
    GL.glVertex3f(-1, 1, 0.0)
    GL.glVertex3f(1, -1, 0.0)
    GL.glEnd()

    # Z-Offset
    if z_offset:
        GL.glLineWidth(1)
        GL.glColor3f(1.0, 0.0, 1.0)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(-2, -1, z_offset)
        GL.glVertex3f(2, 2, z_offset)
        GL.glVertex3f(-2, 2, z_offset)
        GL.glVertex3f(2, -2, z_offset)
        GL.glEnd()

    # Zero-X
    GL.glColor3f(0.5, 0.0, 0.0)
    GL.glBegin(GL.GL_LINES)
    GL.glVertex3f(0.0, start_y, mill_depth)
    GL.glVertex3f(0.0, end_y, mill_depth)
    GL.glEnd()
    # Zero-Y
    GL.glColor3f(0.0, 0.0, 0.5)
    GL.glBegin(GL.GL_LINES)
    GL.glVertex3f(start_x, 0.0, mill_depth)
    GL.glVertex3f(end_x, 0.0, mill_depth)
    GL.glEnd()

    if project["setup"]["view"]["ruler_show"]:
        # MinMax-X
        GL.glColor3f(0.5, 0.0, 0.0)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(min_max[0], start_y - 5, mill_depth)
        GL.glVertex3f(min_max[0], end_y, mill_depth)
        GL.glVertex3f(min_max[2], start_y - 5, mill_depth)
        GL.glVertex3f(min_max[2], end_y, mill_depth)
        draw_text(
            f"{round(min_max[0], 2)}",
            min_max[0],
            start_y - 5 - 6,
            mill_depth,
            0.5,
            True,
        )
        draw_text(
            f"{round(min_max[2], 2)}",
            min_max[2],
            start_y - 5 - 6,
            mill_depth,
            0.5,
            True,
        )
        GL.glEnd()
        # MinMax-Y
        GL.glColor3f(0.0, 0.0, 0.5)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(start_x, min_max[1], mill_depth)
        GL.glVertex3f(end_x + 5, min_max[1], mill_depth)
        GL.glVertex3f(start_x, min_max[3], mill_depth)
        GL.glVertex3f(end_x + 5, min_max[3], mill_depth)
        draw_text(
            f"{round(min_max[1], 2)}",
            end_x + 5,
            min_max[1],
            mill_depth,
            0.5,
            False,
            True,
        )
        draw_text(
            f"{round(min_max[3], 2)}",
            end_x + 5,
            min_max[3],
            mill_depth,
            0.5,
            False,
            True,
        )
        GL.glEnd()
        # Size-X
        GL.glColor3f(1.0, 0.0, 0.0)
        GL.glBegin(GL.GL_LINES)
        draw_text(
            f"{round(size_x, 2)}", center_x, start_y - 5 - 6, mill_depth, 0.5, True
        )
        GL.glEnd()
        # Size-Y
        GL.glColor3f(0.0, 0.0, 1.0)
        GL.glBegin(GL.GL_LINES)
        draw_text(
            f"{round(size_y, 2)}", end_x + 5, center_y, mill_depth, 0.5, False, True
        )
        GL.glEnd()


def draw_object_ids(project: dict) -> None:
    """draws the object id's as text"""
    GL.glLineWidth(2)
    GL.glColor3f(0.63, 0.36, 0.11)
    GL.glBegin(GL.GL_LINES)
    for obj_idx, obj in project["objects"].items():
        if obj.get("layer", "").startswith("BREAKS:") or obj.get(
            "layer", ""
        ).startswith("_TABS"):
            continue
        p_x = obj["segments"][0]["start"][0]
        p_y = obj["segments"][0]["start"][1]
        for (x_1, y_1), (x_2, y_2) in font.lines_for_text(f"#{obj_idx}"):
            GL.glVertex3f(p_x + x_1, p_y + y_1, 5.0)
            GL.glVertex3f(p_x + x_2, p_y + y_2, 5.0)
    GL.glEnd()


def bulge_points(segment):
    points = []
    (
        center,
        start_angle,  # pylint: disable=W0612
        end_angle,  # pylint: disable=W0612
        radius,  # pylint: disable=W0612
    ) = ezdxf.math.bulge_to_arc(segment.start, segment.end, segment.bulge)
    while start_angle > end_angle:
        start_angle -= math.pi
    steps = abs(start_angle - end_angle) / 10
    angle = start_angle + steps
    if start_angle < end_angle:
        while angle < end_angle:
            ap_x = center[0] + radius * math.sin(angle + math.pi / 2)
            ap_y = center[1] - radius * math.cos(angle + math.pi / 2)
            points.append((ap_x, ap_y))
            angle += steps

    return points


def draw_object_edges(project: dict, selected: int = -1) -> None:
    """draws the edges of an object"""
    unit = project["setup"]["machine"]["unit"]
    depth = project["setup"]["mill"]["depth"]
    tabs_height = project["setup"]["tabs"]["height"]
    interpolate = project["setup"]["view"]["arcs"]
    unitscale = 1.0
    if unit == "inch":
        unitscale = 25.4
        depth *= unitscale
        tabs_height *= unitscale

    for obj_idx, obj in project["objects"].items():
        if obj.get("layer", "").startswith("BREAKS:") or obj.get(
            "layer", ""
        ).startswith("_TABS"):
            continue
        if obj_idx == selected:
            GL.glLineWidth(5)
            GL.glColor4f(1.0, 0.0, 0.0, 1.0)
        else:
            GL.glLineWidth(1)
            GL.glColor4f(1.0, 1.0, 1.0, 1.0)

        # side
        GL.glBegin(GL.GL_LINES)
        for segment in obj.segments:
            p_x = segment.start[0]
            p_y = segment.start[1]
            GL.glVertex3f(p_x, p_y, 0.0)
            GL.glVertex3f(p_x, p_y, depth)
        GL.glEnd()

        # top
        GL.glBegin(GL.GL_LINES)
        for segment in obj.segments:
            if segment.bulge != 0.0 and interpolate:
                last_x = segment.start[0]
                last_y = segment.start[1]
                for point in bulge_points(segment):
                    GL.glVertex3f(last_x, last_y, 0.0)
                    GL.glVertex3f(point[0], point[1], 0.0)
                    last_x = point[0]
                    last_y = point[1]
                GL.glVertex3f(last_x, last_y, 0.0)
                GL.glVertex3f(segment.end[0], segment.end[1], 0.0)
            else:
                GL.glVertex3f(segment.start[0], segment.start[1], 0.0)
                GL.glVertex3f(segment.end[0], segment.end[1], 0.0)
        GL.glEnd()

        # bottom
        GL.glBegin(GL.GL_LINES)
        for segment in obj.segments:
            if segment.bulge != 0.0 and interpolate:
                last_x = segment.start[0]
                last_y = segment.start[1]
                for point in bulge_points(segment):
                    GL.glVertex3f(last_x, last_y, depth)
                    GL.glVertex3f(point[0], point[1], depth)
                    last_x = point[0]
                    last_y = point[1]
                GL.glVertex3f(last_x, last_y, depth)
                GL.glVertex3f(segment.end[0], segment.end[1], depth)
            else:
                GL.glVertex3f(segment.start[0], segment.start[1], depth)
                GL.glVertex3f(segment.end[0], segment.end[1], depth)
        GL.glEnd()

        # start points
        start = obj.get("start", ())
        if start:
            depth = 0.1
            GL.glLineWidth(5)
            GL.glColor4f(1.0, 1.0, 0.0, 1.0)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(start[0] - 1, start[1] - 1, depth)
            GL.glVertex3f(start[0] + 1, start[1] + 1, depth)
            GL.glVertex3f(start[0] - 1, start[1] + 1, depth)
            GL.glVertex3f(start[0] + 1, start[1] - 1, depth)
            GL.glEnd()

    # tabs
    tabs = project.get("tabs", {}).get("data", ())
    if tabs:
        tabs_depth = depth + tabs_height
        GL.glLineWidth(5)
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)
        GL.glBegin(GL.GL_LINES)
        for tab in tabs:
            GL.glVertex3f(tab[0][0], tab[0][1], tabs_depth)
            GL.glVertex3f(tab[1][0], tab[1][1], tabs_depth)
        GL.glEnd()


def draw_object_faces(project: dict) -> None:
    """draws the top and side faces of an object"""
    unit = project["setup"]["machine"]["unit"]
    depth = project["setup"]["mill"]["depth"]
    interpolate = project["setup"]["view"]["arcs"]
    color = project["setup"]["view"]["color"]
    alpha = project["setup"]["view"]["alpha"]
    unitscale = 1.0
    if unit == "inch":
        unitscale = 25.4
        depth *= unitscale

    # object faces (side)
    GL.glColor4f(color[0], color[1], color[2], alpha)
    for obj in project["objects"].values():
        if obj.get("layer", "").startswith("BREAKS:") or obj.get(
            "layer", ""
        ).startswith("_TABS"):
            continue
        for segment in obj.segments:
            last_x = segment.start[0]
            last_y = segment.start[1]
            if segment.bulge != 0.0 and interpolate:
                for point in bulge_points(segment):
                    GL.glBegin(GL.GL_TRIANGLE_STRIP)
                    GL.glVertex3f(last_x, last_y, 0.0)
                    GL.glVertex3f(last_x, last_y, depth)
                    GL.glVertex3f(point[0], point[1], 0.0)
                    GL.glVertex3f(point[0], point[1], depth)
                    GL.glEnd()
                    last_x = point[0]
                    last_y = point[1]
            GL.glBegin(GL.GL_TRIANGLE_STRIP)
            GL.glVertex3f(last_x, last_y, 0.0)
            GL.glVertex3f(last_x, last_y, depth)
            GL.glVertex3f(segment.end[0], segment.end[1], 0.0)
            GL.glVertex3f(segment.end[0], segment.end[1], depth)
            GL.glEnd()

    # object faces (top)
    GL.glColor4f(color[0], color[1], color[2], alpha)
    tess = gluNewTess()
    gluTessProperty(tess, GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_ODD)
    gluTessCallback(tess, GLU_TESS_BEGIN, GL.glBegin)
    gluTessCallback(tess, GLU_TESS_VERTEX, GL.glVertex)
    gluTessCallback(tess, GLU_TESS_END, GL.glEnd)
    gluTessCallback(
        tess, GLU_TESS_COMBINE, lambda _points, _vertices, _weights: _points
    )
    gluTessBeginPolygon(tess, 0)
    for obj in project["objects"].values():
        if obj.get("layer", "").startswith("BREAKS:") or obj.get(
            "layer", ""
        ).startswith("_TABS"):
            continue

        if obj.closed:
            gluTessBeginContour(tess)
            for segment in obj.segments:
                p_xy = (segment.start[0], segment.start[1], 0.0)
                gluTessVertex(tess, p_xy, p_xy)
                if segment.bulge != 0.0 and interpolate:
                    for point in bulge_points(segment):
                        p_xy = (point[0], point[1], 0.0)
                        gluTessVertex(tess, p_xy, p_xy)
                p_xy = (segment.end[0], segment.end[1], 0.0)
                gluTessVertex(tess, p_xy, p_xy)
            gluTessEndContour(tess)

    gluTessEndPolygon(tess)
    gluDeleteTess(tess)


def draw_line(p_1: dict, p_2: dict, options: str, project: dict) -> None:
    """callback function for Parser to draw the lines"""
    if project["setup"]["machine"]["g54"]:
        p_from = (p_1["X"], p_1["Y"], p_1["Z"])
        p_to = (p_2["X"], p_2["Y"], p_2["Z"])
    else:
        unit = project["setup"]["machine"]["unit"]
        unitscale = 1.0
        if unit == "inch":
            unitscale = 25.4
        p_from = (
            p_1["X"] - project["setup"]["workpiece"]["offset_x"] * unitscale,
            p_1["Y"] - project["setup"]["workpiece"]["offset_y"] * unitscale,
            p_1["Z"] - project["setup"]["workpiece"]["offset_z"] * unitscale,
        )
        p_to = (
            p_2["X"] - project["setup"]["workpiece"]["offset_x"] * unitscale,
            p_2["Y"] - project["setup"]["workpiece"]["offset_y"] * unitscale,
            p_2["Z"] - project["setup"]["workpiece"]["offset_z"] * unitscale,
        )
    line_width = project["setup"]["tool"]["diameter"]
    mode = project["setup"]["view"]["path"]

    project["simulation_data"].append((p_from, p_to, line_width, mode, options))

    draw_mill_line(p_from, p_to, line_width, mode, options)


def draw_machinecode_path(project: dict) -> bool:
    """draws the machinecode path"""
    project["simulation_data"] = []
    GL.glLineWidth(2)
    try:
        if project["suffix"] in {"ngc", "gcode"}:
            GcodeParser(project["machine_cmd"]).draw(draw_line, (project,))
        elif project["suffix"] in {"hpgl", "hpg"}:
            project["setup"]["machine"]["g54"] = False
            project["setup"]["workpiece"]["offset_z"] = 0.0
            HpglParser(project["machine_cmd"]).draw(draw_line, (project,))
    except Exception as error_string:  # pylint: disable=W0703:
        print(f"ERROR: parsing machine_cmd: {error_string}")
        return False
    return True
