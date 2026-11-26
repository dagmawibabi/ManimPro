/** Manim plugins ManimPro knows how to set up, each with a starter scene that renders. */
export type PluginPreset = {
  id: string;
  /** PyPI name, as passed to pip */
  pkg: string;
  name: string;
  about: string;
  /** Starter scene shipped in the worker's plugin_starters folder */
  starter: string;
  url: string;
  needsLatex?: boolean;
};

export const PLUGINS: PluginPreset[] = [
  {
    id: "slides",
    pkg: "manim-slides",
    name: "manim-slides",
    about: "Turn a scene into a presentation you click through. Present it, or convert it to HTML or PowerPoint.",
    starter: "slides_talk.py",
    url: "https://manim-slides.eertmans.be/",
  },
  {
    id: "ml",
    pkg: "manim-ml",
    name: "ManimML",
    about: "Neural networks and machine-learning diagrams, with forward-pass animations built in.",
    starter: "ml_network.py",
    url: "https://github.com/helblazer811/ManimML",
  },
  {
    id: "chemistry",
    pkg: "manim-chemistry",
    name: "manim-chemistry",
    about: "Elements, Bohr atoms, molecules from files and the periodic table.",
    starter: "chem_atoms.py",
    url: "https://github.com/UnMolDeQuimica/manim-Chemistry",
    needsLatex: true,
  },
];

const norm = (n: string) => n.toLowerCase().replace(/[-_.]+/g, "-");
export const isInstalled = (p: PluginPreset, names: string[]) => names.some((n) => norm(n) === norm(p.pkg));
