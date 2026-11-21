import { authLanguage } from "../cloud";
import { useEffect, useState } from "react";
import App from "../App";
import { AppProvider, initial } from "../lib/store";
import {
  lastProject,
  listProjects,
  readProject,
  rememberProject,
  saveProject,
  type Project,
  type SavedProject,
} from "../lib/projects";
const empty = (): SavedProject => ({
  id: "",
  name: "",
  revision: 0,
  state: { ...initial, lang: authLanguage },
});
async function openWorkspace() {
  const projects = await listProjects();
  const id =
    projects.find((p) => p.id === lastProject())?.id || projects[0]?.id;
  const current = id ? await readProject(id) : empty();
  current.state.lang = authLanguage;
  return { projects, current };
}
export default function ProjectHost() {
  const [workspace, setWorkspace] = useState<{
    projects: Project[];
    current: SavedProject;
  }>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let mounted = true;
    openWorkspace()
      .then((w) => mounted && setWorkspace(w))
      .catch(() => mounted && setFailed(true));
    return () => {
      mounted = false;
    };
  }, []);
  if (!workspace)
    return (
      <p role="status">
        {failed ? "项目存储不可用 · Storage unavailable" : "Loading…"}
      </p>
    );
  async function select(id: string, lang: SavedProject["state"]["lang"]) {
    const current = await readProject(id);
    rememberProject(id);
    setWorkspace(
      (w) =>
        w && {
          ...w,
          current: {
            ...current,
            state: { ...current.state, entered: true, lang },
          },
        },
    );
  }
  async function create(name: string, lang: SavedProject["state"]["lang"]) {
    const current = {
      id: crypto.randomUUID(),
      name,
      revision: 0,
      state: { ...initial, entered: true, lang },
    };
    current.revision = await saveProject(current);
    rememberProject(current.id);
    setWorkspace((w) => w && { projects: [...w.projects, current], current });
  }
  async function reload() {
    setWorkspace(await openWorkspace());
  }
  function renamed(id: string, name: string, revision: number) {
    setWorkspace(
      (w) =>
        w && {
          ...w,
          projects: w.projects.map((p) => (p.id === id ? { ...p, name } : p)),
          current:
            w.current.id === id ? { ...w.current, name, revision } : w.current,
        },
    );
  }
  async function removed(id: string, lang: SavedProject["state"]["lang"]) {
    const projects = await listProjects();
    if (id !== workspace!.current.id) {
      setWorkspace((w) => w && { ...w, projects });
      return;
    }
    const current = projects.length
      ? await readProject(projects[0].id)
      : empty();
    current.state.lang = lang;
    rememberProject(current.id);
    setWorkspace({ projects, current });
  }
  return (
    <AppProvider
      project={workspace.current}
      projects={workspace.projects}
      select={select}
      create={create}
      renamed={renamed}
      removed={removed}
      reload={reload}
    >
      <App />
    </AppProvider>
  );
}
