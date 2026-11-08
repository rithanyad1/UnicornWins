import Link from "next/link";
import { Heading } from "@/components/ui/primitives";

export default function NotFound() {
  return <main id="main" className="page"><Heading title="Nothing here yet" subtitle="This page or incident could not be found."/><Link className="button button-primary" href="/">Return to your data center →</Link></main>;
}
