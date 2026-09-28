import { mount } from "svelte";
import "./app.css";

// Das Linux-Setup (Setup-AppImage) zeigt statt der App den Assistenten. Beides
// erst bei Bedarf laden: die App startet beim Import Abfragen ans Backend,
// und das gibt es im Setup nicht.
const target = document.getElementById("app")!;
const isSetup = new URLSearchParams(location.search).has("setup") && !!window.setup;

if (isSetup) {
  import("./views/Setup.svelte").then(({ default: Setup }) => mount(Setup, { target }));
} else {
  import("./App.svelte").then(({ default: App }) => mount(App, { target }));
}
