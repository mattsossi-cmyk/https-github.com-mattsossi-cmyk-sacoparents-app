/**
 * Regression tests for CodeInput.
 *
 * The most important behavior — firing onComplete exactly once when the
 * six boxes are all filled — regressed in the initial ship because the
 * completion guard used `!joined.includes("")`, which is a permanent
 * false in JS (every string "includes" the empty string). Lock the
 * contract with these tests so the guard can't silently die again.
 *
 * Uses only `react-dom` + `react-dom/test-utils` (no @testing-library
 * dependency needed).
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { act } from "react-dom/test-utils";

import CodeInput from "./CodeInput";

// Route Link renders inside CodeInput's siblings only for other suites;
// this component itself renders plain inputs so we don't need a Router.

function Harness({ onComplete }) {
  const [value, setValue] = React.useState("");
  return (
    <CodeInput
      value={value}
      onChange={setValue}
      onComplete={onComplete}
      autoFocus={false}
      testidPrefix="test-code"
    />
  );
}

function renderInto(el) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = ReactDOM.createRoot(container);
  act(() => {
    root.render(el);
  });
  return { container, root };
}

function fillDigit(container, idx, digit) {
  const el = container.querySelector(`[data-testid="test-code-${idx}"]`);
  const proto = Object.getPrototypeOf(el);
  const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
  act(() => {
    setter.call(el, digit);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

test("onComplete fires once when all six boxes are filled digit-by-digit", () => {
  const onComplete = jest.fn();
  const { container } = renderInto(<Harness onComplete={onComplete} />);

  fillDigit(container, 0, "1");
  expect(onComplete).not.toHaveBeenCalled();

  for (const [idx, d] of [
    [1, "2"], [2, "3"], [3, "4"], [4, "5"], [5, "6"],
  ]) {
    fillDigit(container, idx, d);
  }

  expect(onComplete).toHaveBeenCalledTimes(1);
  expect(onComplete).toHaveBeenCalledWith("123456");
});

test("onComplete fires when a full 6-digit code is autofilled into box 0", () => {
  const onComplete = jest.fn();
  const { container } = renderInto(<Harness onComplete={onComplete} />);

  // iOS SMS autofill / password managers send the full code into the
  // first box at once — the component spreads it across the six inputs.
  fillDigit(container, 0, "987654");

  expect(onComplete).toHaveBeenCalledTimes(1);
  expect(onComplete).toHaveBeenCalledWith("987654");
});

test("non-digits are stripped and don't fire onComplete", () => {
  const onComplete = jest.fn();
  const { container } = renderInto(<Harness onComplete={onComplete} />);

  fillDigit(container, 0, "abc");
  expect(onComplete).not.toHaveBeenCalled();
});
