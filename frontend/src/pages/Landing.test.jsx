/**
 * Landing smoke render test.
 *
 * WHY THIS EXISTS
 * ---------------
 * A missing / renamed lucide-react import silently ships with hot-reload
 * (the module resolves undefined and only crashes at RENDER time). We
 * caught exactly this bug during the iter181 review — `Briefcase` was
 * removed from the imports even though `ProfessionalConnection` still
 * used it. The home page would have crashed for every unauthenticated
 * visitor.
 *
 * This suite mounts the whole `<Landing />` tree in jsdom and asserts
 * that the marquee test-ids render. If ANY icon or component the page
 * uses becomes undefined, React throws during commit and this test
 * fails — long before a live user sees a blank screen.
 *
 * WHAT WE MOCK
 * ------------
 * - `react-router-dom`: v7 ships as ESM by default; Jest under CRA's
 *   default resolver can't traverse the `exports` field cleanly. The
 *   real router isn't needed for a render smoke test — we just need
 *   `<Link>` / `useNavigate` stubs so Landing renders happily.
 * - `../lib/api`: prevents axios from trying to reach the network in
 *   jsdom.
 * - `./Orientation`: Landing only imports `markOrientationSeen` as a
 *   fire-and-forget side-effect. Stubbing avoids pulling in the
 *   Orientation UI + its downstream imports.
 *
 * Uses the same raw `react-dom/client` + `react-dom/test-utils` pattern
 * as `CodeInput.test.jsx` so no @testing-library dependency is needed.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { act } from "react-dom/test-utils";

// React 18+ requires this flag to be set for `act(...)` to be recognised
// under Jest. Without it every render prints a big "not configured to
// support act(...)" warning that pollutes the test log.
global.IS_REACT_ACT_ENVIRONMENT = true;

// --- mocks ------------------------------------------------------------
// virtual:true tells Jest to not resolve the module on disk (react-router-dom
// v7 ships ESM-first exports that CRA's Jest resolver doesn't traverse).
jest.mock(
  "react-router-dom",
  () => {
    const React = require("react");
    return {
      __esModule: true,
      // <Link to="/x">child</Link> → renders a plain <a href="/x">.
      Link: ({ to, children, ...rest }) =>
        React.createElement(
          "a",
          { href: typeof to === "string" ? to : "#", ...rest },
          children
        ),
      NavLink: ({ to, children, ...rest }) =>
        React.createElement(
          "a",
          { href: typeof to === "string" ? to : "#", ...rest },
          children
        ),
      useNavigate: () => jest.fn(),
      useLocation: () => ({ pathname: "/", search: "", hash: "", state: null }),
      useParams: () => ({}),
      useSearchParams: () => [new URLSearchParams(), jest.fn()],
      BrowserRouter: ({ children }) =>
        React.createElement(React.Fragment, null, children),
      MemoryRouter: ({ children }) =>
        React.createElement(React.Fragment, null, children),
      Routes: ({ children }) => React.createElement(React.Fragment, null, children),
      Route: () => null,
      Navigate: () => null,
    };
  },
  { virtual: true }
);
jest.mock("../lib/api", () => ({
  __esModule: true,
  api: {
    get: jest.fn(() => new Promise(() => {})),
    post: jest.fn(() => new Promise(() => {})),
    put: jest.fn(() => new Promise(() => {})),
    delete: jest.fn(() => new Promise(() => {})),
  },
  API: "http://mocked-api",
}));
jest.mock("./Orientation", () => ({
  __esModule: true,
  markOrientationSeen: jest.fn(),
  hasSeenOrientation: jest.fn(() => true),
  default: () => null,
}));

// eslint-disable-next-line import/first
import Landing from "./Landing";
// eslint-disable-next-line import/first
import { AuthProvider } from "../context/AuthContext";

function mount() {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = ReactDOM.createRoot(container);
  act(() => {
    root.render(
      React.createElement(
        AuthProvider,
        null,
        React.createElement(Landing, null)
      )
    );
  });
  return { container, root };
}

describe("<Landing /> smoke render", () => {
  test("renders without throwing (guards against missing imports)", () => {
    // The whole point: if any lucide-react icon or child component is
    // undefined (like the iter181 Briefcase bug), React throws here
    // and the test fails loudly.
    expect(() => mount()).not.toThrow();
  });

  test("ecosystem strip, individual→joint bridge, and professional-connection card all render", () => {
    const { container } = mount();

    // Marquee sections that must be present on the home page.
    // If any of these is missing, either the page has regressed or a
    // component crashed silently at render time.
    const musts = [
      "ecosystem-flow",
      "ecosystem-node-parents",
      "ecosystem-node-professionals",
      "ecosystem-node-result",
      "three-reports-situation",
      "three-reports-foundation",
      "three-reports-child-needs",
      "individual-to-joint-bridge",
      "joint-journey-card",
      "joint-journey-see-sample",
      "professional-connection",
      "professional-connection-invitation-cta",
      "professional-connection-align-cta",
    ];
    for (const tid of musts) {
      const el = container.querySelector(`[data-testid="${tid}"]`);
      expect(el).not.toBeNull();
    }
  });

  test("lucide icons throughout the page resolved to real elements", () => {
    // Belt-and-suspenders: every SVG that ships from lucide-react
    // carries the .lucide class. Assert we rendered a healthy number
    // so an accidental import removal that silently drops a whole
    // component is caught here too.
    const { container } = mount();
    const lucideSvgs = container.querySelectorAll("svg.lucide");
    expect(lucideSvgs.length).toBeGreaterThan(10);
  });
});
