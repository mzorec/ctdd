namespace Shop.Application.Settings;

/// <summary>
/// The routes orders travel on, bound once from the `Orders:Routes` configuration section.
/// Each route names the client it serves and the queue it writes to.
/// </summary>
public sealed class OrderRoutesSettings
{
    public const string SectionName = "Orders:Routes";

    public IReadOnlyCollection<OrderRoute> Routes { get; init; } = [];
}

public sealed record OrderRoute(string Client, string Queue);
