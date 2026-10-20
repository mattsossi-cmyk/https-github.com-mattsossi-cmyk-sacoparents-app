import { accessLogHref, fillCaseCode } from "./accessLogHref";

const T = "https://sacoparentsalign.com/who-can-see?case={case_id}";
const G = "https://sacoparentsalign.com/who-can-see";

describe("accessLogHref", () => {
  it("linked parent with a case code gets their case page", () => {
    expect(accessLogHref({ linked: true, code: "SA-783115", template: T, general: G })).toBe(
      "https://sacoparentsalign.com/who-can-see?case=SA-783115",
    );
  });

  it("linked parent without a code gets the plain page, never an empty ?case=", () => {
    for (const code of [null, undefined, "", "not-a-code", "SA-"]) {
      const href = accessLogHref({ linked: true, code, template: T, general: G });
      expect(href).toBe(G);
      expect(href).not.toContain("?case=");
    }
  });

  it("parents not linked to Align see no link", () => {
    expect(accessLogHref({ linked: false, code: "SA-783115", template: T, general: G })).toBeNull();
    expect(accessLogHref({ linked: undefined, code: null, template: T, general: G })).toBeNull();
  });

  it("no addresses configured -> hidden", () => {
    expect(accessLogHref({ linked: true, code: "SA-783115", template: "", general: "" })).toBeNull();
  });

  it("fillCaseCode only accepts SA- codes", () => {
    expect(fillCaseCode(T, "SA-ABC123")).toBe("https://sacoparentsalign.com/who-can-see?case=SA-ABC123");
    expect(fillCaseCode(T, "x&y=1")).toBeNull();
  });
});
