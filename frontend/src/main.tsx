import { render } from "preact";

import { App } from "./App";
import "./styles.css";
import { initTheme } from "./theme";

initTheme();
render(<App />, document.getElementById("app")!);
