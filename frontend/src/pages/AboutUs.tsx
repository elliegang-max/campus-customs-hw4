import './AboutUs.css'

export default function AboutUs() {
  return (
    <div className="page about">
      <div className="page-header" data-reveal>
        <p className="eyebrow">Since the first press</p>
        <h1>About Campus Customs</h1>
        <p>
          We are a campus apparel shop in New Haven, and we have spent a long time
          learning what students actually want to wear.
        </p>
      </div>

      <section data-reveal>
        <h2>Who we are</h2>
        <p>
          Campus Customs started with a single press and a short list of regulars —
          a crew team that needed hoodies before a meet, a suite that wanted
          matching crewnecks for a reunion weekend. The list got longer. These days
          we keep more than a hundred styles on the racks and still take the
          one-off jobs, because those are the ones people keep for twenty years.
        </p>
        <p>
          Everything we make is meant to survive a New Haven winter, a few hundred
          wash cycles, and whatever happens the weekend of The Game.
        </p>
      </section>

      <section data-reveal>
        <h2>What we make</h2>
        <p>
          The catalogue runs from lightweight tri-blend tees to heavyweight
          crewnecks, quarter-zips and full-zip fleece, in sizes XS through XXL. We
          stock gear for all fourteen residential colleges, for every varsity
          program, for the graduate and professional schools, and for the families
          who show up on move-in day wanting something with Yale on it.
        </p>
        <p>
          For custom work, we screen print and embroider in house. Send us artwork
          or a rough description, and we will come back with a proof, a sizing run
          and an honest turnaround date.
        </p>
      </section>

      <section data-reveal>
        <h2>How we work</h2>
        <ul className="values">
          <li>
            <h3>Straight answers about stock</h3>
            <p>
              If your size is not on the shelf, we will say so rather than quietly
              substituting something close.
            </p>
          </li>
          <li>
            <h3>Nothing we would not wear</h3>
            <p>
              Every style on the site is one we have handled, washed and checked
              ourselves before putting it up.
            </p>
          </li>
          <li>
            <h3>Group orders done properly</h3>
            <p>
              One invoice, one delivery date, and a real person to call when the
              roster changes two days before the deadline.
            </p>
          </li>
        </ul>
      </section>

      <section className="note">
        <p>
          Campus Customs is a fictional shop used as a class project. It is not
          affiliated with, endorsed by, or a partner of Yale University or any
          actual retailer.
        </p>
      </section>
    </div>
  )
}
