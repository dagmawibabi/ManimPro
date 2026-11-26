// Editor completions for the manim API surface people reach for most.
// [label, kind, detail, snippet?]
type Kind = "Class" | "Function" | "Constant" | "Snippet" | "Method";
export const MANIM_COMPLETIONS: [string, Kind, string, string?][] = [
  ["scene", "Snippet", "New Scene class", "class ${1:MyScene}(Scene):\n    def construct(self):\n        ${0:pass}"],
  ["self.play", "Method", "Animate", "self.play(${0})"],
  ["self.wait", "Method", "Pause", "self.wait(${1:1})"],
  ["self.add", "Method", "Add without animation", "self.add(${0})"],
  ["self.next_section", "Method", "Start a new section", 'self.next_section("${1:name}")'],
  [
    "voiceover",
    "Snippet",
    "Narrated scene (stays in sync)",
    "from manimpro_voice import VoiceoverScene\n\n\nclass ${1:Narrated}(VoiceoverScene):\n    def construct(self):\n        with self.voiceover(\"${2:What this part says.}\") as v:\n            ${0:self.play(Create(Circle()), run_time=v.duration)}",
  ],
  ["with self.voiceover", "Snippet", "Speak a line while animating", 'with self.voiceover("${1:text}") as v:\n    ${0:self.play(..., run_time=v.duration)}'],
  // Scenes
  ...(["Scene", "MovingCameraScene", "ThreeDScene", "ZoomedScene"] as const).map(
    (n) => [n, "Class", "Scene type"] as [string, Kind, string],
  ),
  // Mobjects
  ...([
    "Text", "MarkupText", "Paragraph", "Tex", "MathTex", "Code",
    "Circle", "Square", "Rectangle", "RoundedRectangle", "Triangle", "Polygon", "RegularPolygon",
    "Line", "Arrow", "DoubleArrow", "Vector", "DashedLine", "Arc", "Dot", "Ellipse", "Annulus", "Star",
    "Brace", "BraceLabel", "SurroundingRectangle", "BackgroundRectangle", "Cross", "Underline",
    "VGroup", "Group", "VMobject", "ImageMobject", "SVGMobject",
    "Axes", "NumberPlane", "NumberLine", "ThreeDAxes", "BarChart", "ParametricFunction", "FunctionGraph",
    "DecimalNumber", "Integer", "Variable", "ValueTracker", "TracedPath", "Table", "Matrix",
    "Sphere", "Cube", "Prism", "Surface",
  ] as const).map((n) => [n, "Class", "Mobject"] as [string, Kind, string]),
  // Animations
  ...([
    "Create", "Uncreate", "Write", "Unwrite", "DrawBorderThenFill", "FadeIn", "FadeOut",
    "GrowFromCenter", "GrowFromPoint", "GrowArrow", "SpinInFromNothing", "ShrinkToCenter",
    "Transform", "ReplacementTransform", "TransformMatchingShapes", "TransformMatchingTex",
    "FadeTransform", "MoveToTarget", "ApplyMethod", "Rotate", "Rotating", "MoveAlongPath",
    "Indicate", "Circumscribe", "Flash", "FocusOn", "Wiggle", "ShowPassingFlash",
    "AnimationGroup", "Succession", "LaggedStart", "LaggedStartMap", "Wait",
  ] as const).map((n) => [n, "Function", "Animation"] as [string, Kind, string]),
  ["always_redraw", "Function", "Rebuild a mobject every frame"],
  // Constants
  ...([
    "UP", "DOWN", "LEFT", "RIGHT", "ORIGIN", "UL", "UR", "DL", "DR", "IN", "OUT", "PI", "TAU", "DEGREES",
    "WHITE", "BLACK", "GREY", "BLUE", "TEAL", "GREEN", "YELLOW", "GOLD", "RED", "MAROON", "PURPLE", "PINK", "ORANGE",
    "BOLD", "ITALIC", "linear", "smooth", "there_and_back", "rate_functions",
  ] as const).map((n) => [n, "Constant", "manim constant"] as [string, Kind, string]),
];
