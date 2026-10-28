import type { Site } from "@/types";

/**
 * The site coordinate is the Wikidata point for the Sanchi complex (Q181123).
 * It is not used as a geofence for a single stupa, because it is the complex point.
 * Cover photograph: Bernard Gagnon, “Stupa 1, Sanchi 02.jpg”, CC BY-SA 3.0, Wikimedia Commons.
 * That photograph is attached only to the Great Stupa, which it depicts.
 */
const STUPA_CREDIT = {
  author: "Bernard Gagnon",
  license: "CC BY-SA 3.0",
  source: "Wikimedia Commons",
} as const;

export const SANCHI_STUPA: Site = {
  id: "sanchi-stupa",
  slug: "sanchi-stupa",
  name: "Sanchi Stupa",
  city: "Sanchi, Madhya Pradesh",
  country: "India",
  description:
    "The Buddhist complex at Sanchi, known for the Great Stupa and its carved stone gateways.",
  overview:
    "Sanchi is a Buddhist complex in Madhya Pradesh. Its best-known monument is the Great Stupa, a brick mound attributed to the Mauryan emperor Ashoka in the 3rd century BCE and later enlarged and cased in stone. Four carved gateways stand around it. UNESCO inscribed the Buddhist Monuments at Sanchi in 1989. Checkpoints here do not use a location fence, because the available coordinate belongs to the complex rather than to one structure.",
  latitude: 23.47944444,
  longitude: 77.73972222,
  coverImage: "/references/sanchi-stupa-1.jpg",
  coverAlt: "The Great Stupa at Sanchi, with its stone gateways",
  coverCredit: STUPA_CREDIT,
  checkpoints: [
    {
      id: "sanchi-great-stupa",
      slug: "great-stupa",
      name: "Great Stupa",
      category: "stupa",
      shortDescription: "Stupa 1, the principal mound at Sanchi.",
      story:
        "The Great Stupa, also called Stupa 1, began as a brick mound attributed to Ashoka in the 3rd century BCE. Later builders enlarged it and faced it with stone. A harmika crowns the dome, a stone railing encloses the mound, and a processional path runs around it. The reference photograph shows this stupa. It is not used for the gateways or the other stupas.",
      referenceImageUrl: "/references/sanchi-stupa-1.jpg",
      referenceImageUrls: ["/references/sanchi-stupa-1.jpg"],
      imageCredit: STUPA_CREDIT,
      sortOrder: 1,
    },
    {
      id: "sanchi-toranas",
      slug: "toranas",
      name: "Gateways",
      category: "gate",
      shortDescription: "The four carved stone gateways of the Great Stupa.",
      story:
        "Four stone gateways, or toranas, stand at the cardinal directions of the Great Stupa. They are commonly dated to the 1st century BCE. Their carvings include Buddhist symbols and stories of the Buddha’s previous lives. They do not have a separate reference photograph, so the scanner will not treat a view of the whole stupa as a match for the gateways.",
      sortOrder: 2,
    },
    {
      id: "sanchi-ashokan-pillar",
      slug: "ashokan-pillar",
      name: "Ashokan pillar",
      category: "pillar",
      shortDescription: "A polished stone pillar associated with Ashoka.",
      story:
        "A polished stone pillar associated with Ashoka stands near the Great Stupa. Its lion capital is kept in the Sanchi Archaeological Museum, not on the shaft. No reference photograph or separate coordinate for the pillar is on record in this guide.",
      sortOrder: 3,
    },
    {
      id: "sanchi-stupa-3",
      slug: "stupa-3",
      name: "Stupa 3",
      category: "stupa",
      shortDescription: "A smaller stupa near the Great Stupa, excavated in the 19th century.",
      story:
        "Stupa 3 is a smaller mound beside the Great Stupa. In 1851, Alexander Cunningham’s excavation found relic caskets inscribed with the names of the Buddha’s disciples Sariputta and Mahamoggallana. It has no reference photograph or location point in this guide.",
      sortOrder: 4,
    },
  ],
};
