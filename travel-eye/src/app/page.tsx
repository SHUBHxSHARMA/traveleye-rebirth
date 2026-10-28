import Image from "next/image";
import { ButtonLink } from "@/components/Button";
import { DestinationSearch } from "@/components/DestinationSearch";
import { RED_FORT } from "@/lib/data/red-fort";

const guide = RED_FORT.checkpoints.find((checkpoint) => checkpoint.id === "diwan-i-khas");

export default function HomePage() {
  return (
    <div>
      <section className="mx-auto grid max-w-6xl items-center gap-8 px-5 py-10 md:grid-cols-12 md:gap-12 md:px-8 md:py-14">
        <div className="md:col-span-5">
          <p className="text-xs uppercase tracking-[0.2em] text-accent">Delhi · A camera companion</p>
          <h1 className="mt-4 font-display text-5xl leading-[1.02] text-primary md:text-7xl">
            See Beyond the Monument.
          </h1>
          <p className="mt-6 max-w-md text-lg leading-relaxed">
            Raise your phone to a gate, a hall, or a carved wall. Travel Eye finds the place on record and opens the history written for it.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/start" className="w-full sm:w-auto">
              Start Exploring
            </ButtonLink>
            <ButtonLink href="/destinations" variant="secondary" className="w-full sm:w-auto">
              Discover Destinations
            </ButtonLink>
          </div>
        </div>
        <div className="relative h-64 sm:h-80 md:col-span-7 md:h-[36rem]">
          <Image
            src={RED_FORT.coverImage}
            alt="Lahori Gate of the Red Fort in Delhi"
            fill
            priority
            className="object-cover object-[center_35%]"
            sizes="(min-width: 768px) 58vw, 100vw"
          />
        </div>
      </section>

      <section className="border-y border-line">
        <div className="mx-auto max-w-6xl px-5 py-10 md:px-8 md:py-14">
          <DestinationSearch variant="home" />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">Featured destination</p>
        <div className="mt-6 grid items-stretch gap-8 md:grid-cols-12 md:gap-12">
          <div className="relative min-h-72 md:col-span-7 md:min-h-[32rem]">
            <Image
              src="/references/delhi-fort.jpg"
              alt="The outer sandstone walls and Lahori Gate of the Red Fort, Delhi"
              fill
              className="object-cover"
              sizes="(min-width: 768px) 58vw, 100vw"
            />
          </div>
          <div className="flex flex-col justify-center md:col-span-5">
            <p className="text-sm text-muted">
              {RED_FORT.city}, {RED_FORT.country}
            </p>
            <h2 className="mt-2 font-display text-4xl leading-tight text-primary md:text-5xl">{RED_FORT.name}</h2>
            <p className="mt-5 max-w-prose text-base leading-relaxed">{RED_FORT.description}</p>
            <p className="mt-4 text-sm text-muted">{RED_FORT.checkpoints.length} places to find, from the gate to the royal tower.</p>
            <ButtonLink href={`/explore/${RED_FORT.slug}`} className="mt-8 w-fit">
              Explore the Red Fort
            </ButtonLink>
          </div>
        </div>
      </section>

      <section className="border-t border-line bg-surface">
        <div className="mx-auto grid max-w-6xl gap-12 px-5 py-16 md:grid-cols-12 md:px-8 md:py-24">
          <div className="md:col-span-5">
            <p className="text-xs uppercase tracking-[0.2em] text-accent">How the lens works</p>
            <h2 className="mt-3 font-display text-4xl leading-tight text-primary md:text-5xl">
              One photograph, compared with the place itself.
            </h2>
            <div className="relative mt-8 min-h-72">
              <Image
                src="/references/naubat-khana.jpg"
                alt="Naubat Khana, the drum house inside the Red Fort"
                fill
                className="object-cover"
                sizes="(min-width: 768px) 40vw, 100vw"
              />
            </div>
            <p className="mt-3 text-sm text-muted">Naubat Khana, Red Fort</p>
          </div>
          <ol className="md:col-span-6 md:col-start-7">
            {[
              {
                title: "Stand at the site",
                text: "Open the scanner for the destination you are visiting. The Red Fort has a reference photograph for every checkpoint. The other places can still be read where a scan is not yet possible.",
              },
              {
                title: "Capture or upload",
                text: "Use the live camera, or choose a photograph already on your phone. The image is sent to the matcher on this app.",
              },
              {
                title: "Read what matched",
                text: "Travel Eye compares the picture with reference photographs. When one place is close enough, its written history opens.",
              },
            ].map((step, index) => (
              <li key={step.title} className="border-t border-line py-7">
                <p className="text-xs tracking-[0.18em] text-accent">{String(index + 1).padStart(2, "0")}</p>
                <h3 className="mt-2 font-display text-3xl text-primary">{step.title}</h3>
                <p className="mt-3 max-w-prose text-base leading-relaxed">{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 py-16 md:grid-cols-12 md:px-8 md:py-24">
        <div className="md:col-span-5">
          <p className="text-xs uppercase tracking-[0.2em] text-accent">The travel guide</p>
          <h2 className="mt-3 font-display text-4xl leading-tight text-primary md:text-5xl">
            The explanation stays with the landmark.
          </h2>
          <p className="mt-5 max-w-prose text-base leading-relaxed">
            After a photograph matches, Travel Eye shows the history kept for that place and can read it aloud. The words come from the destination record. This version does not open a chat, and it will not invent a further answer.
          </p>
        </div>
        {guide && (
          <figure className="border-l border-gold pl-6 md:col-span-6 md:col-start-7">
            <figcaption className="text-xs uppercase tracking-[0.18em] text-accent">
              {guide.name}
            </figcaption>
            <blockquote className="mt-4 font-display text-2xl font-normal leading-relaxed text-primary">
              {guide.story}
            </blockquote>
            <ButtonLink href={`/explore/${RED_FORT.slug}/checkpoints#checkpoint-${guide.id}`} variant="quiet" className="mt-6">
              Open this place
            </ButtonLink>
          </figure>
        )}
      </section>

      <section className="border-t border-line">
        <div className="mx-auto grid max-w-6xl gap-12 px-5 py-16 md:grid-cols-2 md:px-8 md:py-24">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent">Narration</p>
            <h2 className="mt-3 font-display text-4xl leading-tight text-primary">Heard in the voice already on your phone.</h2>
            <p className="mt-4 max-w-prose leading-relaxed">
              Every story can be read aloud in English through the browser. The language control in Settings remembers that choice. Other languages are not in the record yet, so the app does not pretend to translate.
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent">On this device</p>
            <h2 className="mt-3 font-display text-4xl leading-tight text-primary">What you find stays in the browser.</h2>
            <p className="mt-4 max-w-prose leading-relaxed">
              Your name, saved destinations, and the checkpoints you have found are stored on this phone. Progress is kept separately for each destination. Stories for the places in the guide are part of the app itself. Scanning still needs a connection, because the photograph is compared on the server.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
