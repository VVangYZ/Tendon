import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Workspace from "./Workspace";
import "./styles.css";
import "./sheet.css";
import "./batch.css";
import "./layout.css";
createRoot(document.getElementById("root")!).render(<StrictMode><Workspace /></StrictMode>);
