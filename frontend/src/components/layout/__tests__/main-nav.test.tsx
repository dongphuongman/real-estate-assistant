import { render, screen } from "@testing-library/react"
import { MainNav } from "../main-nav"
import { usePathname } from "next/navigation"

// Mock usePathname
jest.mock("next/navigation", () => ({
  usePathname: jest.fn(),
}))

describe("MainNav", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("renders navigation links", () => {
    (usePathname as jest.Mock).mockReturnValue("/")
    render(<MainNav />)
    
    expect(screen.getByText("Home")).toBeInTheDocument()
    expect(screen.getByText("Search")).toBeInTheDocument()
    expect(screen.getByText("Assistant")).toBeInTheDocument()
    expect(screen.getByText("Analytics")).toBeInTheDocument()
  })

  it("highlights active link", () => {
    (usePathname as jest.Mock).mockReturnValue("/search")
    render(<MainNav />)
    
    const searchLink = screen.getByText("Search").closest("a")
    const homeLink = screen.getByText("Home").closest("a")
    
    expect(searchLink).toHaveClass("text-black dark:text-white")
    expect(homeLink).toHaveClass("text-muted-foreground")
  })
})
