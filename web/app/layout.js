import "./globals.css";

export const metadata = {
  title: "LRN | Investment Banking Interview",
  description: "A structured LRN voice interview practice session.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
